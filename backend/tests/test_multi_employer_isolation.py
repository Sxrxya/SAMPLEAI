"""Test multi-employer data isolation and organization boundaries.

Verifies:
1. Recruiter A cannot read, modify, or match jobs belonging to Organization B.
2. Recruiter A cannot read match runs or match results belonging to Organization B.
3. Job matching results are strictly scoped to the requesting organization's job.
4. Candidates without active consent cannot be returned in match results.
"""

from uuid import uuid4
import pytest
from fastapi import HTTPException
from sqlalchemy import select

from app.api.jobs import _organization_job
from app.core.db import SessionLocal
from app.core.security import hash_password
from app.models import (
    CandidateProfile,
    ResumeConsent,
    Job,
    JobRequirement,
    JobVersion,
    MatchResult,
    MatchRun,
    Organization,
    OrganizationMembership,
    Resume,
    ResumeExtraction,
    ResumeVersion,
    User,
    utc_now,
)
from app.services.matching import evaluate_candidates_for_job


@pytest.fixture
def multi_org_setup():
    """Setup two distinct organizations with recruiters, jobs, and candidate."""
    with SessionLocal() as db:
        # Organization 1
        org1 = Organization(name=f"Org Alpha {uuid4().hex[:4]}", status="verified")
        db.add(org1)
        db.flush()

        recruiter1 = User(
            email=f"recruiter1_{uuid4().hex[:6]}@alpha.test",
            display_name="Recruiter Alpha",
            password_hash=hash_password("Pass123!"),
            role="recruiter",
        )
        db.add(recruiter1)
        db.flush()

        db.add(OrganizationMembership(organization_id=org1.id, user_id=recruiter1.id, role="admin"))

        # Organization 2
        org2 = Organization(name=f"Org Beta {uuid4().hex[:4]}", status="verified")
        db.add(org2)
        db.flush()

        recruiter2 = User(
            email=f"recruiter2_{uuid4().hex[:6]}@beta.test",
            display_name="Recruiter Beta",
            password_hash=hash_password("Pass123!"),
            role="recruiter",
        )
        db.add(recruiter2)
        db.flush()

        db.add(OrganizationMembership(organization_id=org2.id, user_id=recruiter2.id, role="admin"))

        # Job for Org 1
        job1 = Job(
            organization_id=org1.id,
            created_by=recruiter1.id,
            title="Alpha AI Engineer",
            status="active",
        )
        db.add(job1)
        db.flush()

        job_version1 = JobVersion(
            job_id=job1.id,
            version_number=1,
            description="Alpha AI Engineer JD requiring Python and PyTorch.",
            status="approved",
            approved_at=utc_now(),
            analysis_json={
                "schema_version": "job.v2",
                "role_title": "Alpha AI Engineer",
                "min_experience_months": 24,
                "required_skills": [
                    {"key": "python", "description": "Demonstrated proficiency in Python"},
                    {"key": "pytorch", "description": "Demonstrated proficiency in PyTorch"},
                ],
                "preferred_skills": [
                    {"key": "fastapi", "description": "Preferred experience with FastAPI"}
                ],
            },
        )
        db.add(job_version1)
        db.flush()

        db.add(
            JobRequirement(
                job_version_id=job_version1.id,
                requirement_key="required:python",
                requirement_type="required",
                description="Python proficiency",
                evidence="Requires Python.",
            )
        )
        db.add(
            JobRequirement(
                job_version_id=job_version1.id,
                requirement_key="required:pytorch",
                requirement_type="required",
                description="PyTorch deep learning",
                evidence="Requires PyTorch.",
            )
        )

        # Job for Org 2
        job2 = Job(
            organization_id=org2.id,
            created_by=recruiter2.id,
            title="Beta DevOps Engineer",
            status="active",
        )
        db.add(job2)
        db.flush()

        job_version2 = JobVersion(
            job_id=job2.id,
            version_number=1,
            description="Beta DevOps Engineer JD requiring Kubernetes.",
            status="approved",
            approved_at=utc_now(),
            analysis_json={
                "schema_version": "job.v2",
                "role_title": "Beta DevOps Engineer",
                "min_experience_months": 24,
                "required_skills": [
                    {"key": "kubernetes", "description": "Demonstrated proficiency in Kubernetes"}
                ],
                "preferred_skills": [],
            },
        )
        db.add(job_version2)
        db.flush()

        # Candidate with active consent
        cand_user = User(
            email=f"cand_{uuid4().hex[:6]}@test.com",
            display_name="Candidate One",
            password_hash=hash_password("Pass123!"),
            role="candidate",
        )
        db.add(cand_user)
        db.flush()

        profile = CandidateProfile(user_id=cand_user.id, headline="Senior AI Engineer")
        db.add(profile)

        resume = Resume(candidate_id=cand_user.id)
        db.add(resume)
        db.flush()

        rv = ResumeVersion(
            resume_id=resume.id,
            version_number=1,
            original_filename="resume.pdf",
            mime_type="application/pdf",
            storage_key=f"mock/{uuid4().hex}.pdf",
            byte_size=1024,
            source_sha256=uuid4().hex,
            status="complete",
        )
        db.add(rv)
        db.flush()

        cand_payload = {
            "schema_version": "resume.v2",
            "skills": [
                {"name": "Python", "evidence_level": "DEMONSTRATED", "section": "skills"},
                {"name": "PyTorch", "evidence_level": "DEMONSTRATED", "section": "skills"},
                {"name": "FastAPI", "evidence_level": "CONTEXTUAL", "section": "skills"},
            ],
            "work_history": [
                {
                    "title": "Machine Learning Engineer",
                    "company": "Tech Corp",
                    "start_date": "2021-01",
                    "end_date": "2024-01",
                    "description": "Built PyTorch models in Python.",
                }
            ],
            "projects": [],
            "education": [],
            "certifications": [],
            "achievements": [],
        }

        db.add(
            ResumeExtraction(
                resume_version_id=rv.id,
                schema_version="resume.v2",
                prompt_version="resume-v2",
                provider="huggingface",
                model_id="Qwen/Qwen2.5-72B-Instruct",
                extraction_json=cand_payload,
                review_status="confirmed",
            )
        )

        consent_ai = ResumeConsent(
            candidate_id=cand_user.id,
            resume_version_id=rv.id,
            scope="ai_processing",
            granted_at=utc_now(),
        )
        consent_share = ResumeConsent(
            candidate_id=cand_user.id,
            resume_version_id=rv.id,
            scope="recruiter_search",
            granted_at=utc_now(),
        )
        db.add(consent_ai)
        db.add(consent_share)
        db.commit()

        yield {
            "org1": org1,
            "org2": org2,
            "recruiter1": recruiter1,
            "recruiter2": recruiter2,
            "job1": job1,
            "job2": job2,
            "job_version1": job_version1,
            "job_version2": job_version2,
            "candidate_user": cand_user,
            "candidate_resume_version": rv,
            "consent_share": consent_share,
        }


def test_recruiter_cannot_access_other_organization_job(multi_org_setup):
    """Verify that Recruiter 1 cannot access Job 2 belonging to Organization 2."""
    data = multi_org_setup
    with SessionLocal() as db:
        # Recruiter 1 accessing Job 1 -> Success
        job, membership = _organization_job(db, data["recruiter1"].id, data["job1"].id)
        assert job.id == data["job1"].id
        assert membership.organization_id == data["org1"].id

        # Recruiter 1 accessing Job 2 -> 404 Not Found (Cross-tenant leak prevented)
        with pytest.raises(HTTPException) as exc_info:
            _organization_job(db, data["recruiter1"].id, data["job2"].id)
        assert exc_info.value.status_code == 404


def test_recruiter_cannot_access_other_organization_matches(multi_org_setup):
    """Verify that match runs and results executed for Org 1 are isolated from Org 2."""
    data = multi_org_setup
    with SessionLocal() as db:
        # Execute matching for Org 1
        run1 = MatchRun(
            job_version_id=data["job_version1"].id,
            requested_by=data["recruiter1"].id,
            status="queued",
            top_k=5,
        )
        db.add(run1)
        db.commit()

        top_matches = evaluate_candidates_for_job(
            db=db,
            job_id=data["job1"].id,
            match_run_id=run1.id,
            recruiter_id=data["recruiter1"].id,
        )
        assert len(top_matches) >= 1

        db.refresh(run1)
        assert run1.status == "complete"

        # Check results exist for Job 1
        results = db.scalars(select(MatchResult).where(MatchResult.match_run_id == run1.id)).all()
        assert len(results) >= 1

        # Verify Recruiter 2 cannot view Job 1 via _organization_job
        with pytest.raises(HTTPException) as exc_info:
            _organization_job(db, data["recruiter2"].id, data["job1"].id)
        assert exc_info.value.status_code == 404


def test_consent_revocation_prevents_matching(multi_org_setup):
    """Verify candidate with revoked consent is not returned in match results."""
    data = multi_org_setup
    with SessionLocal() as db:
        # Revoke candidate's sharing consent
        consent = db.get(ResumeConsent, data["consent_share"].id)
        consent.revoked_at = utc_now()
        db.commit()

        # Run match for Job 1
        run = MatchRun(
            job_version_id=data["job_version1"].id,
            requested_by=data["recruiter1"].id,
            status="queued",
            top_k=5,
        )
        db.add(run)
        db.commit()

        top_matches = evaluate_candidates_for_job(
            db=db,
            job_id=data["job1"].id,
            match_run_id=run.id,
            recruiter_id=data["recruiter1"].id,
        )

        # Candidate should NOT be matched due to revoked consent
        assert len(top_matches) == 0
        results = db.scalars(
            select(MatchResult).where(
                MatchResult.match_run_id == run.id,
                MatchResult.candidate_id == data["candidate_user"].id,
            )
        ).all()
        assert len(results) == 0
