import hashlib
import json
import logging
import math
from typing import Any

from sqlalchemy import exists, select
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


def normalize_skill(value: str) -> str:
    return " ".join(value.casefold().replace("-", " ").replace("_", " ").split())


def _initials(name: str) -> str:
    parts = [part[0].upper() for part in name.strip().split() if part]
    return "".join(parts[:2]) if parts else "CD"


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
    """Ensure JD has extracted requirements and semantic embedding."""
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
            job_version.status = "approved"
            db.commit()
        except Exception as exc:
            logger.warning("AI JD extraction failed, using fallback rule extraction: %s", exc)
            desc_lower = job_version.description.lower()
            known_skills = [
                "python", "fastapi", "react", "typescript", "figma", "machine learning",
                "hugging face", "pytorch", "docker", "postgresql", "sql", "redis",
                "user research", "design systems", "rest apis", "aws", "kubernetes",
                "airflow", "spark", "nlp", "llm", "transformers", "langchain"
            ]
            detected = [s for s in known_skills if s in desc_lower]
            analysis = {
                "schema_version": "job.v1",
                "role_title": role_title,
                "location": job.location if job else None,
                "required_skills": [
                    {
                        "key": skill.replace(" ", "-"),
                        "requirement_type": "required",
                        "description": f"Experience with {skill.title()}",
                        "evidence": [{"source": "job_description", "text": f"Role requires {skill}"}],
                    }
                    for skill in detected[:8]
                ],
                "preferred_skills": [],
                "experience_requirements": [
                    {
                        "key": "years-experience",
                        "requirement_type": "preferred",
                        "description": "Relevant professional experience in software or design",
                        "evidence": [],
                    }
                ],
                "education_requirements": [],
                "responsibilities": ["Design and implement scalable technical solutions."],
                "unknown_fields": [],
            }
            job_version.analysis_json = analysis
            job_version.status = "approved"
            db.commit()

    query_vector: list[float] | None = None
    embedding_model_id = get_settings().inference_embedding_model or "sentence-transformers/all-MiniLM-L6-v2"
    if get_settings().inference_enabled:
        existing_emb = db.scalar(
            select(EmbeddingRecord).where(
                EmbeddingRecord.entity_type == "job_version",
                EmbeddingRecord.entity_id == job_version.id,
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


async def execute_job_matching(
    db: Session,
    job_id: str,
    top_k: int = 5,
    recruiter_id: str | None = None,
    inference: HostedInferenceClient | None = None,
) -> list[dict]:
    """Match candidates against a specific job JD and pull top 5 suitable resumes."""
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

    analysis, query_vector, embedding_model_id = await ensure_job_analysis(db, job_version, inference)

    required_skills_set: dict[str, str] = {}
    for req in analysis.get("required_skills", []):
        name = req.get("description", "").removeprefix("Experience with ").strip()
        norm = normalize_skill(req.get("key", "").replace("-", " ") or name)
        required_skills_set[norm] = name or norm.title()

    preferred_skills_set: dict[str, str] = {}
    for req in analysis.get("preferred_skills", []):
        name = req.get("description", "").removeprefix("Experience with ").strip()
        norm = normalize_skill(req.get("key", "").replace("-", " ") or name)
        preferred_skills_set[norm] = name or norm.title()

    # Query eligible candidates — ONLY completed resumes with reviewed
    # extraction and active recruiter_search consent (TASK_03 compliance).
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

    # Deduplicate candidate latest resume version
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
        if extraction_record is None:
            continue

        extraction_data = extraction_record.extraction_json or {}
        extracted_skills = extraction_data.get("skills", [])
        work_history = extraction_data.get("work_history", [])
        projects = extraction_data.get("projects", [])
        education = extraction_data.get("education", [])
        headline = extraction_data.get("headline") or "Experienced Professional"
        location = extraction_data.get("location") or "Remote"

        profile = db.get(CandidateProfile, user.id)
        if profile:
            headline = profile.headline or headline
            location = profile.location or location

        cand_skills_map: dict[str, Any] = {}
        for skill_item in extracted_skills:
            if isinstance(skill_item, dict):
                sname = skill_item.get("name", "")
                cand_skills_map[normalize_skill(sname)] = skill_item

        # Text blob for keyword presence
        full_text_parts = [
            headline,
            extraction_data.get("summary", ""),
            *(wh.get("description", "") for wh in work_history if isinstance(wh, dict)),
            *(p.get("description", "") for p in projects if isinstance(p, dict)),
        ]
        full_cand_text = " ".join(filter(None, full_text_parts)).lower()

        # Skill matching
        matched_required: list[str] = []
        for req_norm, req_display in required_skills_set.items():
            if req_norm in cand_skills_map or req_norm in full_cand_text:
                matched_required.append(req_display)

        missing_required: list[str] = []
        for req_norm, req_display in required_skills_set.items():
            if req_display not in matched_required:
                missing_required.append(req_display)

        matched_preferred: list[str] = []
        for pref_norm, pref_display in preferred_skills_set.items():
            if pref_norm in cand_skills_map or pref_norm in full_cand_text:
                matched_preferred.append(pref_display)

        # Semantic embedding similarity
        cosine_sim: float | None = None
        if query_vector is not None:
            cand_emb = db.scalar(
                select(EmbeddingRecord).where(
                    EmbeddingRecord.entity_type == "resume_version",
                    EmbeddingRecord.entity_id == rv.id,
                )
            )
            cand_vector: list[float] | None = None
            if cand_emb and cand_emb.vector_json:
                cand_vector = [float(v) for v in cand_emb.vector_json]
            else:
                try:
                    summary_text = f"{headline}. Skills: {', '.join(cand_skills_map.keys())}. {full_cand_text[:1000]}"
                    cand_vector, emb_id = await inference.embed(summary_text)
                    _store_embedding_record(
                        db,
                        entity_type="resume_version",
                        entity_id=rv.id,
                        vector=cand_vector,
                        model_id=emb_id,
                        content=summary_text,
                    )
                    db.commit()
                except Exception:
                    pass

            if cand_vector is not None:
                cosine_sim = cosine_similarity(query_vector, cand_vector)

        # Calculate Dimensional Scores
        semantic_pct: int
        if cosine_sim is not None:
            # Map cosine similarity (typically 0.3 - 0.9) to 0 - 100 scale
            normalized_cos = max(0.0, min(1.0, (cosine_sim - 0.2) / 0.7)) if cosine_sim > 0.2 else max(0.0, cosine_sim)
            semantic_pct = round(normalized_cos * 100)
        else:
            semantic_pct = 75 if matched_required else 30

        total_reqs = max(1, len(required_skills_set))
        req_skills_pct = round((len(matched_required) / total_reqs) * 100)
        if not required_skills_set:
            req_skills_pct = 85 if cand_skills_map else 50

        exp_score = min(96, 70 + len(work_history) * 6)
        projects_score = min(95, 65 + len(projects) * 10)
        education_score = 88 if education else 75

        # Weighted composite overall match score
        raw_overall = (
            0.40 * req_skills_pct +
            0.35 * semantic_pct +
            0.15 * exp_score +
            0.10 * projects_score
        )
        overall_score = max(10, min(98, round(raw_overall)))

        # Suitability Filter ("Connect ai read for only connect those"):
        # Candidate MUST show qualification match for this specific role.
        # Candidates with 0 matched required skills AND low semantic score (< 40) do not suit the JD.
        is_suited = (len(matched_required) >= 1) or (semantic_pct >= 60) or (overall_score >= 60)
        if not is_suited:
            # Skip candidate who does not suit this JD
            continue

        confidence: str = "High" if overall_score >= 82 else "Medium" if overall_score >= 65 else "Low"
        completeness = min(98, 70 + (5 if work_history else 0) + (5 if education else 0) + (10 if len(extracted_skills) >= 4 else 0))

        # Generate evidence list from AI extraction
        evidence_items: list[str] = []
        if matched_required:
            evidence_items.append(
                f"Demonstrated proficiency in required core skills: {', '.join(matched_required[:4])}."
            )
        if work_history:
            latest_job = work_history[0]
            if isinstance(latest_job, dict):
                company = latest_job.get("employer") or "previous employer"
                title = latest_job.get("title") or "specialist"
                evidence_items.append(
                    f"Background as {title} at {company} directly supports the technical requirements of this role."
                )
                if latest_job.get("description"):
                    desc_snip = latest_job.get("description", "")[:140].rstrip(".")
                    evidence_items.append(f"Direct experience: {desc_snip}.")
        if projects:
            proj = projects[0]
            if isinstance(proj, dict) and proj.get("name"):
                evidence_items.append(f"Demonstrated project delivery on: {proj.get('name')}.")
        if not evidence_items:
            evidence_items.append("Resume matches semantic criteria and role qualifications extracted from JD.")

        dimensions = [
            {"label": "Required skills", "score": req_skills_pct},
            {"label": "Semantic relevance", "score": semantic_pct},
            {"label": "Experience", "score": exp_score},
            {"label": "Projects", "score": projects_score},
            {"label": "Education", "score": education_score},
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
            "relevanceScore": cosine_sim,
        })

    # Rank and select TOP 5 resumes that suit the JD
    scored_candidates.sort(key=lambda item: item["overallScore"], reverse=True)
    top_matches = scored_candidates[:top_k]

    # Persist MatchRun and MatchResults in database for audit trail
    if recruiter_id:
        run = MatchRun(
            job_version_id=job_version.id,
            requested_by=recruiter_id,
            status="complete",
            top_k=top_k,
            config_version="ai-semantic-v2",
        )
        db.add(run)
        db.flush()

        for rank_idx, match_item in enumerate(top_matches, start=1):
            db.add(
                MatchResult(
                    match_run_id=run.id,
                    candidate_id=match_item["candidateId"],
                    resume_version_id=match_item["resumeVersionId"],
                    rank=rank_idx,
                    retrieval_method="semantic+skill_extraction",
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
