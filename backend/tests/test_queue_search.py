from concurrent.futures import ThreadPoolExecutor

from app.core.db import SessionLocal
from app.models import (
    ProcessingJob,
    Resume,
    ResumeConsent,
    ResumeExtraction,
    ResumeVersion,
    User,
)
from app.services.queue import claim_next_job
from app.services.search import eligible_resume_search, upsert_resume_search


def test_concurrent_queue_claims_are_unique():
    with SessionLocal() as db:
        db.add_all(
            [
                ProcessingJob(
                    entity_type="resume_version",
                    entity_id=f"version-{index}",
                    job_type="resume_extract",
                    idempotency_key=f"queue-{index}",
                )
                for index in range(24)
            ]
        )
        db.commit()

    with ThreadPoolExecutor(max_workers=12) as executor:
        claimed = list(executor.map(lambda _: claim_next_job(), range(24)))
    claimed_ids = [item for item in claimed if item is not None]
    assert len(claimed_ids) == 24
    assert len(set(claimed_ids)) == 24


def test_fts_retrieval_requires_review_and_active_consent():
    with SessionLocal() as db:
        candidate = User(
            email="search@example.com",
            display_name="Search Candidate",
            password_hash="unused-in-test",
            role="candidate",
        )
        db.add(candidate)
        db.flush()
        resume = Resume(candidate_id=candidate.id)
        db.add(resume)
        db.flush()
        version = ResumeVersion(
            resume_id=resume.id,
            version_number=1,
            original_filename="resume.pdf",
            storage_key=f"{candidate.id}/test.pdf",
            mime_type="application/pdf",
            byte_size=100,
            source_sha256="a" * 64,
            status="complete",
        )
        db.add(version)
        db.flush()
        db.add(
            ResumeExtraction(
                resume_version_id=version.id,
                schema_version="resume.v1",
                prompt_version="test-v1",
                provider="test",
                model_id="test-model",
                extraction_json={"schema_version": "resume.v1"},
                review_status="confirmed",
            )
        )
        consent = ResumeConsent(
            candidate_id=candidate.id,
            resume_version_id=version.id,
            scope="recruiter_search",
        )
        db.add(consent)
        upsert_resume_search(
            db,
            resume_version_id=version.id,
            candidate_id=candidate.id,
            searchable_text="Python FastAPI backend engineer",
        )
        db.commit()

        assert len(eligible_resume_search(db, "FastAPI engineer", 10)) == 1
        consent.revoked_at = version.created_at
        db.commit()
        assert eligible_resume_search(db, "FastAPI engineer", 10) == []
