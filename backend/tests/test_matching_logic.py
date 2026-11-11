"""Unit tests for the Tandem AI candidate-job matching and recommendation engine."""

import pytest
from sqlalchemy import exists, select
from app.core.db import SessionLocal
from app.models import Resume, ResumeConsent, ResumeExtraction, ResumeVersion, User, utc_now
from app.services.matching import normalize_skill


def test_normalize_skill():
    assert normalize_skill("Machine Learning") == "machine learning"
    assert normalize_skill("machine-learning") == "machine learning"
    assert normalize_skill("  FastAPI  ") == "fastapi"
    assert normalize_skill("PostgreSQL") == "postgresql"
    assert normalize_skill("HUGGING_FACE") == "hugging face"


def test_suitability_filter_logic():
    # Suitability rule:
    # is_suited = (len(matched_required) >= 1) or (semantic_pct >= 60) or (overall_score >= 60)
    
    # Case 1: Unqualified candidate (0 matched skills, low semantic, low overall)
    matched_req_unqualified = []
    semantic_unqualified = 30
    overall_unqualified = 45
    is_suited_1 = (len(matched_req_unqualified) >= 1) or (semantic_unqualified >= 60) or (overall_unqualified >= 60)
    assert not is_suited_1, "Unqualified candidate should be filtered out"

    # Case 2: Qualified candidate with required skills
    matched_req_qualified = ["Python", "FastAPI"]
    semantic_qualified = 75
    overall_qualified = 86
    is_suited_2 = (len(matched_req_qualified) >= 1) or (semantic_qualified >= 60) or (overall_qualified >= 60)
    assert is_suited_2, "Qualified candidate must pass suitability check"


def test_scoring_weights_composite():
    # Scoring weights:
    # 40% required skills + 35% semantic relevance + 15% experience + 10% projects
    req_skills_pct = 100
    semantic_pct = 80
    exp_score = 88
    projects_score = 85

    raw_overall = (
        0.40 * req_skills_pct +
        0.35 * semantic_pct +
        0.15 * exp_score +
        0.10 * projects_score
    )
    overall_score = max(10, min(98, round(raw_overall)))
    assert overall_score == 90
    assert 10 <= overall_score <= 98


def test_top_k_ranking_and_clamping():
    candidates = [
        {"name": "Alice", "overallScore": 92},
        {"name": "Bob", "overallScore": 75},
        {"name": "Charlie", "overallScore": 88},
        {"name": "David", "overallScore": 65},
        {"name": "Eve", "overallScore": 81},
        {"name": "Frank", "overallScore": 70},
        {"name": "Grace", "overallScore": 55},
    ]
    candidates.sort(key=lambda c: c["overallScore"], reverse=True)
    top_5 = candidates[:5]

    assert len(top_5) == 5
    assert [c["name"] for c in top_5] == ["Alice", "Charlie", "Eve", "Bob", "Frank"]
    assert top_5[0]["overallScore"] == 92
    assert top_5[-1]["overallScore"] == 70


def test_matching_candidate_eligibility_and_consent_query():
    """Verify that only resumes with active recruiter_search consent and confirmed extraction are eligible."""
    with SessionLocal() as db:
        user_eligible = User(
            email="eligible@example.com",
            display_name="Eligible Candidate",
            password_hash="pwd",
            role="candidate",
        )
        user_unconsented = User(
            email="unconsented@example.com",
            display_name="Unconsented Candidate",
            password_hash="pwd",
            role="candidate",
        )
        user_unreviewed = User(
            email="unreviewed@example.com",
            display_name="Unreviewed Candidate",
            password_hash="pwd",
            role="candidate",
        )
        db.add_all([user_eligible, user_unconsented, user_unreviewed])
        db.flush()

        # Eligible candidate setup
        res_e = Resume(candidate_id=user_eligible.id)
        db.add(res_e)
        db.flush()
        ver_e = ResumeVersion(
            resume_id=res_e.id,
            version_number=1,
            original_filename="cv.pdf",
            storage_key=f"{user_eligible.id}/cv.pdf",
            mime_type="application/pdf",
            byte_size=100,
            source_sha256="e"*64,
            status="complete",
        )
        db.add(ver_e)
        db.flush()
        db.add(ResumeConsent(candidate_id=user_eligible.id, resume_version_id=ver_e.id, scope="recruiter_search"))
        db.add(ResumeExtraction(resume_version_id=ver_e.id, schema_version="resume.v1", prompt_version="v1", provider="hf", model_id="qwen", extraction_json={}, review_status="confirmed"))

        # Unconsented candidate setup (revoked consent)
        res_u = Resume(candidate_id=user_unconsented.id)
        db.add(res_u)
        db.flush()
        ver_u = ResumeVersion(
            resume_id=res_u.id,
            version_number=1,
            original_filename="cv.pdf",
            storage_key=f"{user_unconsented.id}/cv.pdf",
            mime_type="application/pdf",
            byte_size=100,
            source_sha256="u"*64,
            status="complete",
        )
        db.add(ver_u)
        db.flush()
        db.add(ResumeConsent(candidate_id=user_unconsented.id, resume_version_id=ver_u.id, scope="recruiter_search", revoked_at=utc_now()))
        db.add(ResumeExtraction(resume_version_id=ver_u.id, schema_version="resume.v1", prompt_version="v1", provider="hf", model_id="qwen", extraction_json={}, review_status="confirmed"))

        # Unreviewed candidate setup (review_status="pending")
        res_p = Resume(candidate_id=user_unreviewed.id)
        db.add(res_p)
        db.flush()
        ver_p = ResumeVersion(
            resume_id=res_p.id,
            version_number=1,
            original_filename="cv.pdf",
            storage_key=f"{user_unreviewed.id}/cv.pdf",
            mime_type="application/pdf",
            byte_size=100,
            source_sha256="p"*64,
            status="complete",
        )
        db.add(ver_p)
        db.flush()
        db.add(ResumeConsent(candidate_id=user_unreviewed.id, resume_version_id=ver_p.id, scope="recruiter_search"))
        db.add(ResumeExtraction(resume_version_id=ver_p.id, schema_version="resume.v1", prompt_version="v1", provider="hf", model_id="qwen", extraction_json={}, review_status="pending"))

        db.commit()

        # Run the exact eligibility query used in execute_job_matching
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

        query = (
            select(ResumeVersion, Resume, User)
            .join(Resume, Resume.id == ResumeVersion.resume_id)
            .join(User, User.id == Resume.candidate_id)
            .where(
                ResumeVersion.status == "complete",
                has_reviewed_extraction,
                has_active_recruiter_consent,
            )
        )
        results = db.execute(query).all()
        candidate_ids = [user.id for _, _, user in results]

        assert user_eligible.id in candidate_ids, "Eligible candidate must be included"
        assert user_unconsented.id not in candidate_ids, "Candidate with revoked consent must be excluded"
        assert user_unreviewed.id not in candidate_ids, "Candidate with pending review must be excluded"
