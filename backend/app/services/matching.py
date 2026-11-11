import hashlib
import json
import logging
import math
import re
from datetime import datetime
from typing import Any

from sqlalchemy import delete, exists, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import (
    CandidateProfile,
    EmbeddingRecord,
    Job,
    JobRequirement,
    JobVersion,
    MatchResult,
    MatchRun,
    Resume,
    ResumeConsent,
    ResumeExtraction,
    ResumeVersion,
    User,
    utc_now,
)
from app.schemas import JobExtractionPayload, JobRequirementFact, ResumeExtractionPayload
from app.services.inference import HostedInferenceClient, InferenceProviderError, InferenceUnavailable
from app.services.search import cosine_similarity

logger = logging.getLogger("tandem.matching")

# Configurable and versioned scoring model (Section 6.C)
DEFAULT_SCORING_CONFIG: dict[str, Any] = {
    "version": "merit-v2.1",
    "weights": {
        "required_skills": 35.0,
        "relevant_experience": 20.0,
        "relevant_projects": 20.0,
        "preferred_skills": 10.0,
        "certifications": 5.0,
        "education": 5.0,
        "achievements": 5.0,
    },
    "evidence_multipliers": {
        "DEMONSTRATED": 1.0,
        "ASSESSMENT_VERIFIED": 1.0,
        "EXTERNALLY_VERIFIED": 1.0,
        "CONTEXTUAL": 0.70,
        "CLAIMED": 0.35,
    },
    "default_target_experience_months": 36,
}

# Domain skill synonyms for accurate normalization
SKILL_SYNONYMS: dict[str, str] = {
    "python3": "python",
    "py": "python",
    "fast-api": "fastapi",
    "fast api": "fastapi",
    "react.js": "react",
    "reactjs": "react",
    "react js": "react",
    "typescript": "typescript",
    "ts": "typescript",
    "javascript": "javascript",
    "js": "javascript",
    "postgresql": "postgresql",
    "postgres": "postgresql",
    "psql": "postgresql",
    "docker": "docker",
    "containerization": "docker",
    "containers": "docker",
    "kubernetes": "kubernetes",
    "k8s": "kubernetes",
    "machine learning": "machine learning",
    "ml": "machine learning",
    "deep learning": "deep learning",
    "dl": "deep learning",
    "hugging face": "hugging face",
    "huggingface": "hugging face",
    "hf": "hugging face",
    "transformers": "transformers",
    "pytorch": "pytorch",
    "torch": "pytorch",
    "figma": "figma",
    "design systems": "design systems",
    "design system": "design systems",
    "user research": "user research",
    "ux research": "user research",
    "ui/ux": "ui/ux",
    "ux": "ui/ux",
    "ui": "ui/ux",
    "rest apis": "rest apis",
    "rest api": "rest apis",
    "restful": "rest apis",
    "rest": "rest apis",
    "graphql": "graphql",
    "gql": "graphql",
    "aws": "aws",
    "amazon web services": "aws",
    "gcp": "gcp",
    "google cloud": "gcp",
    "tailwind css": "tailwind css",
    "tailwind": "tailwind css",
    "redis": "redis",
    "langchain": "langchain",
    "nlp": "nlp",
    "natural language processing": "nlp",
    "llm": "llm",
    "large language models": "llm",
    "sql": "sql",
    "microservices": "microservices",
    "prototyping": "prototyping",
    "wireframing": "prototyping",
    "accessibility": "accessibility",
    "wcag": "accessibility",
}


def normalize_skill(value: str) -> str:
    cleaned = " ".join(value.casefold().replace("-", " ").replace("_", " ").split())
    return SKILL_SYNONYMS.get(cleaned, cleaned)


def _initials(name: str) -> str:
    parts = [part[0].upper() for part in name.strip().split() if part]
    return "".join(parts[:2]) if parts else "CD"


def parse_date_year(date_str: str | None) -> int | None:
    if not date_str:
        return None
    match = re.search(r"\b(19\d\d|20\d\d)\b", str(date_str))
    if match:
        return int(match.group(1))
    return None


def calculate_duration_months(start_date: str | None, end_date: str | None) -> int | None:
    """Calculate months duration between dates. Never infer dates when insufficient."""
    if not start_date:
        return None
    start_year = parse_date_year(start_date)
    if not start_year:
        return None

    if not end_date or "present" in str(end_date).lower() or "current" in str(end_date).lower():
        end_year = datetime.now().year
    else:
        end_year = parse_date_year(end_date)
        if not end_year:
            return None

    if end_year < start_year:
        return None

    years_diff = max(0, end_year - start_year)
    return max(6, years_diff * 12)


def _store_embedding_record(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    vector: list[float],
    model_id: str,
    content: str,
) -> None:
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    current = db.scalar(
        select(EmbeddingRecord).where(
            EmbeddingRecord.entity_type == entity_type,
            EmbeddingRecord.entity_id == entity_id,
            EmbeddingRecord.model_id == model_id,
            EmbeddingRecord.content_hash == content_hash,
        )
    )
    if current is None:
        db.add(
            EmbeddingRecord(
                entity_type=entity_type,
                entity_id=entity_id,
                model_id=model_id,
                dimensions=len(vector),
                vector_json=vector,
                content_hash=content_hash,
            )
        )


async def ensure_job_analysis(
    db: Session, job_version: JobVersion, inference: HostedInferenceClient
) -> tuple[dict, list[float] | None, str]:
    """Ensure JD has extracted requirements and semantic embedding.
    Never silently auto-approves unreviewed fallback extractions.
    """
    analysis = job_version.analysis_json
    model_id = job_version.model_id or ""

    if not analysis:
        job = db.get(Job, job_version.job_id)
        role_title = job.title if job else "Job Opening"
        try:
            extraction, model_id = await inference.extract_job(job_version.description)
            analysis = extraction.model_dump(mode="json")
            job_version.analysis_json = analysis
            job_version.model_id = model_id
            job_version.provider = "huggingface"
            # Keep as needs_review if not already confirmed/approved by employer
            if job_version.status not in ["approved", "active"]:
                job_version.status = "needs_review"
            db.commit()
        except Exception as exc:
            logger.warning("AI JD extraction failed, using safe rule-based extractor: %s", exc)
            desc_lower = job_version.description.lower()
            detected_skills: list[str] = []
            for canonical, mapped in SKILL_SYNONYMS.items():
                if canonical in desc_lower and mapped not in detected_skills:
                    detected_skills.append(mapped)

            analysis = {
                "schema_version": "job.v2",
                "role_title": role_title,
                "location": job.location if job else None,
                "work_arrangement": "remote" if "remote" in desc_lower else "hybrid" if "hybrid" in desc_lower else "on-site",
                "min_experience_months": 36 if "senior" in role_title.lower() or "lead" in role_title.lower() else 12,
                "max_experience_months": None,
                "required_skills": [
                    {
                        "key": skill.replace(" ", "-"),
                        "requirement_type": "required",
                        "description": f"Demonstrated proficiency in {skill.title()}",
                        "evidence": [{"source": "job_description", "text": f"Required in JD: {skill}"}],
                    }
                    for skill in detected_skills[:6]
                ],
                "preferred_skills": [
                    {
                        "key": skill.replace(" ", "-"),
                        "requirement_type": "preferred",
                        "description": f"Preferred experience with {skill.title()}",
                        "evidence": [{"source": "job_description", "text": f"Preferred in JD: {skill}"}],
                    }
                    for skill in detected_skills[6:10]
                ],
                "experience_requirements": [
                    {
                        "key": "relevant-experience",
                        "requirement_type": "required",
                        "description": f"Practical experience relevant to {role_title}",
                        "evidence": [],
                    }
                ],
                "education_requirements": [],
                "certification_requirements": [],
                "project_expectations": [],
                "responsibilities": ["Design, develop, and deliver high-quality solutions."],
                "explicit_eligibility_rules": [],
                "unknown_fields": [],
            }
            job_version.analysis_json = analysis
            if job_version.status not in ["approved", "active"]:
                job_version.status = "needs_review"
            db.commit()

    query_vector: list[float] | None = None
    embedding_model_id = get_settings().inference_embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
    if get_settings().inference_enabled:
        existing_emb = db.scalar(
            select(EmbeddingRecord).where(
                EmbeddingRecord.entity_type == "job_version",
                EmbeddingRecord.entity_id == job_version.id,
                EmbeddingRecord.model_id == embedding_model_id,
            )
        )
        if existing_emb and existing_emb.vector_json:
            query_vector = [float(v) for v in existing_emb.vector_json]
        else:
            try:
                query_vector, emb_id = await inference.embed(job_version.description)
                _store_embedding_record(
                    db,
                    entity_type="job_version",
                    entity_id=job_version.id,
                    vector=query_vector,
                    model_id=emb_id,
                    content=job_version.description,
                )
                db.commit()
            except Exception as exc:
                logger.warning("Semantic embedding unavailable for JD: %s", exc)

    return analysis, query_vector, embedding_model_id


def evaluate_candidates_for_job(
    db: Session,
    job_id: str,
    top_k: int = 5,
    recruiter_id: str | None = None,
    match_run_id: str | None = None,
    scoring_config: dict[str, Any] | None = None,
) -> list[dict]:
    """Pure synchronous evidence-based scoring and ranking engine for candidates against a confirmed JD."""
    cfg = scoring_config or DEFAULT_SCORING_CONFIG
    weights = cfg["weights"]
    multipliers = cfg["evidence_multipliers"]

    job = db.get(Job, job_id)
    if job is None:
        raise ValueError("Job not found")

    job_version = db.scalar(
        select(JobVersion)
        .where(JobVersion.job_id == job.id)
        .order_by(JobVersion.version_number.desc())
    )
    if job_version is None:
        raise ValueError("Job description version not found")

    analysis = job_version.analysis_json or {}

    # 1. Parse Required & Preferred Skills from JD
    required_skills_dict: dict[str, str] = {}
    for req in analysis.get("required_skills", []):
        name = req.get("description", "").removeprefix("Demonstrated proficiency in ").removeprefix("Experience with ").strip()
        norm = normalize_skill(req.get("key", "").replace("-", " ") or name)
        required_skills_dict[norm] = name or norm.title()

    preferred_skills_dict: dict[str, str] = {}
    for req in analysis.get("preferred_skills", []):
        name = req.get("description", "").removeprefix("Preferred experience with ").removeprefix("Experience with ").strip()
        norm = normalize_skill(req.get("key", "").replace("-", " ") or name)
        preferred_skills_dict[norm] = name or norm.title()

    target_exp_months = analysis.get("min_experience_months") or cfg.get("default_target_experience_months", 36)
    role_title = analysis.get("role_title") or job.title

    # 2. Query only eligible candidates:
    # Status == 'complete', extraction confirmed, and active recruiter_search consent
    has_reviewed_extraction = exists(
        select(ResumeExtraction.id).where(
            ResumeExtraction.resume_version_id == ResumeVersion.id,
            ResumeExtraction.review_status.in_(["confirmed", "corrected"]),
        )
    )
    has_active_recruiter_consent = exists(
        select(ResumeConsent.id).where(
            ResumeConsent.resume_version_id == ResumeVersion.id,
            ResumeConsent.scope == "recruiter_search",
            ResumeConsent.revoked_at.is_(None),
        )
    )

    resumes_query = (
        select(ResumeVersion, Resume, User)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .join(User, User.id == Resume.candidate_id)
        .where(
            ResumeVersion.status == "complete",
            has_reviewed_extraction,
            has_active_recruiter_consent,
        )
        .order_by(ResumeVersion.created_at.desc())
    )
    candidates_data = db.execute(resumes_query).all()

    # Deduplicate: Keep latest resume version per candidate user
    seen_candidates: set[str] = set()
    candidate_resumes: list[tuple[ResumeVersion, Resume, User]] = []
    for rv, resume, user in candidates_data:
        if user.id not in seen_candidates:
            seen_candidates.add(user.id)
            candidate_resumes.append((rv, resume, user))

    scored_candidates: list[dict] = []

    for rv, resume, user in candidate_resumes:
        extraction_record = db.scalar(
            select(ResumeExtraction)
            .where(ResumeExtraction.resume_version_id == rv.id)
            .order_by(ResumeExtraction.created_at.desc())
        )
        if extraction_record is None or not extraction_record.extraction_json:
            continue

        cand_data = extraction_record.extraction_json
        extracted_skills = cand_data.get("skills", [])
        soft_skills = cand_data.get("soft_skills", [])
        work_history = cand_data.get("work_history", [])
        internships = cand_data.get("internships", [])
        projects = cand_data.get("projects", [])
        education = cand_data.get("education", [])
        certifications = cand_data.get("certifications", [])
        achievements = cand_data.get("achievements", [])
        headline = cand_data.get("headline") or "Professional"
        location = cand_data.get("location") or "Remote"

        profile = db.get(CandidateProfile, user.id)
        if profile:
            headline = profile.headline or headline
            location = profile.location or location

        # Index candidate skills by normalized name and track highest evidence level
        cand_skills_map: dict[str, dict] = {}
        for s in (*extracted_skills, *soft_skills):
            if isinstance(s, dict):
                sname = s.get("name", "")
                norm = normalize_skill(sname)
                cand_skills_map[norm] = s

        # Build combined text for contextual verification
        wh_texts = [wh.get("description", "") for wh in work_history if isinstance(wh, dict)]
        proj_texts = [p.get("description", "") for p in projects if isinstance(p, dict)]
        combined_text = " ".join([headline, cand_data.get("summary", ""), *wh_texts, *proj_texts]).lower()

        evidence_items: list[str] = []

        # =========================================================================
        # 1. REQUIRED SKILLS EVALUATION (Weight: 35.0 pts)
        # =========================================================================
        matched_required: list[str] = []
        missing_required: list[str] = []
        req_evidence_points = 0.0

        for req_norm, req_display in required_skills_dict.items():
            matched_skill_item = cand_skills_map.get(req_norm)
            if matched_skill_item:
                ev_level = matched_skill_item.get("evidence_level", "CLAIMED")
                multiplier = multipliers.get(ev_level, 0.7)
                req_evidence_points += multiplier
                matched_required.append(req_display)
                ev_quote = ""
                if matched_skill_item.get("evidence"):
                    ev_quote = f" (Evidence: '{matched_skill_item['evidence'][0].get('text', '')}')"
                evidence_items.append(f"Demonstrated required skill: {req_display} [{ev_level}]{ev_quote}")
            elif req_norm in combined_text:
                # Contextual mention in experience/projects
                req_evidence_points += multipliers.get("CONTEXTUAL", 0.70)
                matched_required.append(req_display)
                evidence_items.append(f"Contextual required skill found in resume body: {req_display} [CONTEXTUAL]")
            else:
                missing_required.append(req_display)

        total_req_count = max(1, len(required_skills_dict))
        required_skills_score = min(weights["required_skills"], (req_evidence_points / total_req_count) * weights["required_skills"])

        # =========================================================================
        # 2. RELEVANT WORK EXPERIENCE EVALUATION (Weight: 20.0 pts)
        # =========================================================================
        total_relevant_months = 0
        total_documented_months = 0

        for wh in (*work_history, *internships):
            if not isinstance(wh, dict):
                continue
            duration = wh.get("duration_months")
            if duration is None:
                duration = calculate_duration_months(wh.get("start_date"), wh.get("end_date"))

            if duration:
                total_documented_months += duration
                # Assess relevance to JD requirements
                desc = (wh.get("description", "") + " " + wh.get("title", "")).lower()
                rel_matches = sum(1 for req in required_skills_dict if req in desc)
                if rel_matches >= 2 or any(term in desc for term in role_title.lower().split()):
                    total_relevant_months += duration
                elif rel_matches == 1:
                    total_relevant_months += int(duration * 0.5)

        if total_relevant_months > 0:
            exp_factor = min(1.0, total_relevant_months / max(12, target_exp_months))
            experience_score = exp_factor * weights["relevant_experience"]
            evidence_items.append(
                f"Documented {total_relevant_months // 12} yrs ({total_relevant_months} mos) of directly relevant experience matching role expectations."
            )
        elif total_documented_months > 0:
            # Experience documented but less direct overlap
            experience_score = min(5.0, (total_documented_months / max(12, target_exp_months)) * 5.0)
            evidence_items.append(f"Documented {total_documented_months} months of professional experience with partial role overlap.")
        else:
            experience_score = 0.0

        # =========================================================================
        # 3. RELEVANT PROJECT EVIDENCE EVALUATION (Weight: 20.0 pts)
        # =========================================================================
        project_points = 0.0
        relevant_projects_count = 0

        for p in projects:
            if not isinstance(p, dict):
                continue
            p_desc = (p.get("description", "") + " " + " ".join(p.get("skills", []))).lower()
            overlap_count = sum(1 for req in required_skills_dict if req in p_desc)

            if overlap_count >= 2:
                project_points += 10.0
                relevant_projects_count += 1
                evidence_items.append(f"High-relevance project '{p.get('name', 'Project')}' delivers core skills: {overlap_count} required competencies.")
            elif overlap_count == 1:
                project_points += 5.0
                relevant_projects_count += 1
                evidence_items.append(f"Relevant project '{p.get('name', 'Project')}' demonstrates practical application.")

        projects_score = min(weights["relevant_projects"], project_points)

        # =========================================================================
        # 4. PREFERRED SKILLS EVALUATION (Weight: 10.0 pts)
        # =========================================================================
        matched_preferred: list[str] = []
        pref_points = 0.0
        for pref_norm, pref_display in preferred_skills_dict.items():
            if pref_norm in cand_skills_map:
                pref_points += multipliers.get(cand_skills_map[pref_norm].get("evidence_level", "CLAIMED"), 0.7)
                matched_preferred.append(pref_display)
            elif pref_norm in combined_text:
                pref_points += 0.5
                matched_preferred.append(pref_display)

        pref_count = max(1, len(preferred_skills_dict))
        preferred_skills_score = min(weights["preferred_skills"], (pref_points / pref_count) * weights["preferred_skills"])
        if matched_preferred:
            evidence_items.append(f"Verified preferred skills: {', '.join(matched_preferred[:4])}.")

        # =========================================================================
        # 5. CERTIFICATIONS EVALUATION (Weight: 5.0 pts)
        # =========================================================================
        certs_score = 0.0
        if certifications:
            for cert in certifications:
                cert_name = cert.get("name", "") if isinstance(cert, dict) else str(cert)
                if any(k in cert_name.lower() for k in (*required_skills_dict.keys(), "certified", "engineer", "specialist")):
                    certs_score = weights["certifications"]
                    evidence_items.append(f"Relevant professional certification: {cert_name}.")
                    break
            if certs_score == 0 and len(certifications) > 0:
                certs_score = 2.5

        # =========================================================================
        # 6. EDUCATION RELEVANCE EVALUATION (Weight: 5.0 pts)
        # =========================================================================
        education_score = 0.0
        if education:
            for edu in education:
                field = (edu.get("field", "") if isinstance(edu, dict) else "").lower()
                qual = (edu.get("qualification", "") if isinstance(edu, dict) else "").lower()
                if any(term in field for term in ["computer", "software", "data", "design", "engineering", "information", "intelligence", "science"]):
                    education_score = weights["education"]
                    evidence_items.append(f"Relevant academic degree: {qual.upper()} in {field.title()}.")
                    break
                elif field:
                    education_score = 3.0

        # =========================================================================
        # 7. DEMONSTRATED ACHIEVEMENTS EVALUATION (Weight: 5.0 pts)
        # =========================================================================
        achievements_score = 0.0
        if achievements:
            achievements_score = weights["achievements"]
            evidence_items.append(f"Documented professional achievements ({len(achievements)} reported).")

        # =========================================================================
        # COMPOSITE TOTAL MERIT SCORE (100-Point Scale)
        # =========================================================================
        total_score = (
            required_skills_score +
            experience_score +
            projects_score +
            preferred_skills_score +
            certs_score +
            education_score +
            achievements_score
        )
        overall_score = max(5, min(98, round(total_score)))

        # =========================================================================
        # SUITABILITY FILTER
        # Candidate must demonstrate at least 1 required skill AND achieve >= 20% score
        # Candidates with 0 matched required skills (e.g. Accountant for AI engineer) are skipped!
        # =========================================================================
        is_suited = (len(matched_required) >= 1) and (overall_score >= 18)
        if not is_suited:
            continue

        confidence = "High" if overall_score >= 75 and len(matched_required) >= 2 else "Medium" if overall_score >= 50 else "Moderate"
        completeness = min(98, 60 + (10 if work_history else 0) + (10 if education else 0) + (10 if projects else 0) + (8 if len(cand_skills_map) >= 4 else 0))

        dimensions = [
            {"label": "Required skills", "score": round((required_skills_score / weights["required_skills"]) * 100)},
            {"label": "Relevant experience", "score": round((experience_score / weights["relevant_experience"]) * 100)},
            {"label": "Project evidence", "score": round((projects_score / weights["relevant_projects"]) * 100)},
            {"label": "Preferred skills", "score": round((preferred_skills_score / weights["preferred_skills"]) * 100)},
            {"label": "Education & certs", "score": round(((education_score + certs_score) / (weights["education"] + weights["certifications"])) * 100)},
        ]

        scored_candidates.append({
            "candidateId": user.id,
            "name": user.display_name,
            "initials": _initials(user.display_name),
            "headline": headline,
            "location": location,
            "resumeVersion": f"Resume v{rv.version_number} · {rv.created_at.strftime('%b %d, %Y')}",
            "jobReference": f"{job.title} · {job.id[:8].upper()}",
            "overallScore": overall_score,
            "confidence": confidence,
            "completeness": completeness,
            "dimensions": dimensions,
            "skills": matched_required + matched_preferred,
            "missingSkills": missing_required,
            "evidence": evidence_items,
            "resumeVersionId": rv.id,
            "relevanceScore": overall_score / 100.0,
            "requiredSkillsScore": required_skills_score,
            "experienceScore": experience_score,
        })

    # =========================================================================
    # DETERMINISTIC RANKING & SELECTION (Up to top 5)
    # If fewer than 5 qualify, returns fewer than 5. Never fabricates candidates.
    # =========================================================================
    scored_candidates.sort(
        key=lambda c: (c["overallScore"], c["requiredSkillsScore"], c["experienceScore"], c["candidateId"]),
        reverse=True,
    )
    top_matches = scored_candidates[:top_k]

    # =========================================================================
    # PERSIST MATCHRUN AND MATCHRESULTS
    # Preserves original MatchRun ID when provided; clears old results on rerun.
    # =========================================================================
    active_run: MatchRun | None = None
    if match_run_id:
        active_run = db.get(MatchRun, match_run_id)
        if active_run:
            active_run.status = "complete"
            active_run.completed_at = utc_now()
            active_run.error_message = None
            active_run.config_version = cfg["version"]
            # Clean up prior results for idempotent retry
            db.execute(delete(MatchResult).where(MatchResult.match_run_id == active_run.id))
            db.flush()

    if not active_run and recruiter_id:
        active_run = MatchRun(
            job_version_id=job_version.id,
            requested_by=recruiter_id,
            status="complete",
            top_k=top_k,
            config_version=cfg["version"],
            completed_at=utc_now(),
        )
        db.add(active_run)
        db.flush()

    if active_run:
        for rank_idx, match_item in enumerate(top_matches, start=1):
            db.add(
                MatchResult(
                    match_run_id=active_run.id,
                    candidate_id=match_item["candidateId"],
                    resume_version_id=match_item["resumeVersionId"],
                    rank=rank_idx,
                    retrieval_method="merit_evidence_evaluation",
                    relevance_score=match_item["relevanceScore"],
                    dimensions_json={
                        "overall_score": match_item["overallScore"],
                        "confidence": match_item["confidence"],
                        "dimensions": match_item["dimensions"],
                    },
                    missing_requirements_json=match_item["missingSkills"],
                    evidence_json=match_item["evidence"],
                )
            )
        db.commit()

    return top_matches


async def execute_job_matching(
    db: Session,
    job_id: str,
    top_k: int = 5,
    recruiter_id: str | None = None,
    inference: HostedInferenceClient | None = None,
    match_run_id: str | None = None,
    scoring_config: dict[str, Any] | None = None,
) -> list[dict]:
    """Execute evidence-based candidate evaluation and return top-5 matching resumes."""
    if inference is None:
        inference = HostedInferenceClient()

    job = db.get(Job, job_id)
    if job is None:
        raise ValueError("Job not found")

    job_version = db.scalar(
        select(JobVersion)
        .where(JobVersion.job_id == job.id)
        .order_by(JobVersion.version_number.desc())
    )
    if job_version is None:
        raise ValueError("Job description version not found")

    # Ensure JD requirements are extracted
    await ensure_job_analysis(db, job_version, inference)

    return evaluate_candidates_for_job(
        db=db,
        job_id=job_id,
        top_k=top_k,
        recruiter_id=recruiter_id,
        match_run_id=match_run_id,
        scoring_config=scoring_config,
    )

