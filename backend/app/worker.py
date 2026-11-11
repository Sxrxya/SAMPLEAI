import asyncio
import hashlib
import logging
from pathlib import Path
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.models import (
    EmbeddingRecord,
    JobRequirement,
    JobVersion,
    MatchResult,
    MatchRun,
    ProcessingJob,
    ResumeConsent,
    ResumeExtraction,
    ResumeVersion,
)
from app.schemas import JobExtractionPayload, ResumeExtractionPayload
from app.services.documents import extract_text
from app.services.inference import (
    HostedInferenceClient,
    InferenceProviderError,
    InferenceUnavailable,
)
from app.services.queue import (
    claim_next_job,
    mark_blocked,
    mark_failed,
    mark_succeeded,
)
from app.services.search import (
    cosine_similarity,
    eligible_resume_embeddings,
    eligible_resume_search,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tandem.worker")


def _file_path(storage_key: str) -> Path:
    root = get_settings().storage_root.resolve()
    path = (root / storage_key).resolve()
    if root not in path.parents:
        raise ValueError("unsafe storage key")
    return path


def _store_embedding(
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


async def _process_resume(
    job: ProcessingJob, db: Session, inference: HostedInferenceClient
) -> None:
    version = db.get(ResumeVersion, job.entity_id)
    if version is None:
        raise ValueError("resume version not found")
    ai_consent = db.scalar(
        select(ResumeConsent.id).where(
            ResumeConsent.resume_version_id == version.id,
            ResumeConsent.scope == "ai_processing",
            ResumeConsent.revoked_at.is_(None),
        )
    )
    if ai_consent is None:
        version.status = "needs_consent"
        mark_succeeded(db, job)
        return

    version.status = "processing"
    db.commit()
    source_text = await asyncio.to_thread(extract_text, _file_path(version.storage_key))
    try:
        extraction, actual_model_id = await inference.extract_resume(source_text)
    except Exception as exc:
        logger.warning("AI resume extraction failed, using safe non-fabricating parser: %s", exc)
        actual_model_id = "safe-rule-parser-v2"
        known_skills = [
            "python", "fastapi", "react", "typescript", "figma", "machine learning",
            "hugging face", "pytorch", "docker", "postgresql", "sql", "redis",
            "user research", "design systems", "rest apis", "aws", "kubernetes",
            "airflow", "spark", "nlp", "llm", "transformers", "langchain", "java",
            "c++", "go", "javascript", "html", "css", "node", "express", "graphql"
        ]
        text_lower = source_text.lower()
        detected_skills = [s for s in known_skills if s in text_lower]
        first_line = source_text.splitlines()[0].strip() if source_text.splitlines() else None
        # Safe fallback: NEVER invent missing employers, titles, or dates
        extraction = ResumeExtractionPayload(
            schema_version="resume.v2",
            headline=first_line[:120] if first_line else None,
            summary=source_text[:400].strip(),
            skills=[
                {
                    "name": s.title(),
                    "category": "technical",
                    "evidence_level": "CLAIMED",
                    "evidence": [{"source": "resume_body", "text": f"Found verbatim in resume: {s}"}],
                }
                for s in detected_skills
            ],
            work_history=[],
            internships=[],
            education=[],
            projects=[],
            certifications=[],
            achievements=[],
            publications=[],
            languages=[],
            volunteer_experience=[],
            unknown_fields=["work_history", "education", "projects"],
            field_statuses={
                "skills": "EXTRACTED" if detected_skills else "NOT_FOUND",
                "work_history": "NEEDS_REVIEW",
                "education": "NEEDS_REVIEW",
                "projects": "NEEDS_REVIEW",
            },
            source_text_summary=source_text[:2000].strip(),
        )

    db.add(
        ResumeExtraction(
            resume_version_id=version.id,
            schema_version=extraction.schema_version,
            prompt_version="resume-extraction-v2",
            provider="openai-compatible",
            model_id=actual_model_id,
            extraction_json=extraction.model_dump(mode="json"),
            review_status="pending",
        )
    )
    version.status = "needs_review"

    try:
        vector, embedding_model_id = await inference.embed(extraction.model_dump_json())
        _store_embedding(
            db,
            entity_type="resume_version",
            entity_id=version.id,
            vector=vector,
            model_id=embedding_model_id,
            content=extraction.model_dump_json(),
        )
    except (InferenceUnavailable, InferenceProviderError):
        logger.warning("Embedding unavailable for resume version %s", version.id)
    mark_succeeded(db, job)


async def _process_job_description(
    job: ProcessingJob, db: Session, inference: HostedInferenceClient
) -> None:
    version = db.get(JobVersion, job.entity_id)
    if version is None:
        raise ValueError("job description version not found")
    version.status = "processing"
    db.commit()
    extraction, actual_model_id = await inference.extract_job(version.description)
    version.analysis_json = extraction.model_dump(mode="json")
    version.status = "needs_review"
    version.prompt_version = "job-extraction-v1"
    version.provider = "openai-compatible"
    version.model_id = actual_model_id
    try:
        vector, embedding_model_id = await inference.embed(version.description)
        _store_embedding(
            db,
            entity_type="job_version",
            entity_id=version.id,
            vector=vector,
            model_id=embedding_model_id,
            content=version.description,
        )
    except (InferenceUnavailable, InferenceProviderError):
        logger.warning("Embedding unavailable for job version %s", version.id)
    mark_succeeded(db, job)


def _normalize_skill(value: str) -> str:
    return " ".join(value.casefold().split())


async def _process_match_run(
    job: ProcessingJob, db: Session, inference: HostedInferenceClient
) -> None:
    """Execute match run using the unified merit-based matching service.

    Keeps the original MatchRun ID intact throughout its complete lifecycle
    (queued -> processing -> complete/failed) and records execution metrics.
    """
    from app.services.matching import execute_job_matching

    run = db.get(MatchRun, job.entity_id)
    if run is None:
        raise ValueError("match run not found")
    job_version = db.get(JobVersion, run.job_version_id)
    if job_version is None or job_version.status != "approved":
        run.status = "failed"
        run.error_message = "approved job description not found"
        run.completed_at = utc_now()
        db.commit()
        raise ValueError("approved job description not found")

    run.status = "processing"
    db.commit()

    try:
        await execute_job_matching(
            db,
            job_id=job_version.job_id,
            top_k=run.top_k or 5,
            recruiter_id=run.requested_by,
            inference=inference,
            match_run_id=run.id,
        )
        mark_succeeded(db, job)
    except Exception as exc:
        run.status = "failed"
        run.error_message = str(exc)[:490]
        run.completed_at = utc_now()
        db.commit()
        raise


async def process_job(job_id: str) -> None:
    inference = HostedInferenceClient()
    with SessionLocal() as db:
        job = db.get(ProcessingJob, job_id)
        if job is None:
            return
        try:
            if job.job_type == "resume_extract":
                await _process_resume(job, db, inference)
            elif job.job_type == "jd_analyze":
                await _process_job_description(job, db, inference)
            elif job.job_type == "match_run":
                await _process_match_run(job, db, inference)
            else:
                raise ValueError("unsupported processing job type")
        except InferenceUnavailable:
            version = (
                db.get(ResumeVersion, job.entity_id)
                if job.entity_type == "resume_version"
                else None
            )
            if version is not None and version.status == "processing":
                version.status = "queued"
            job_version = (
                db.get(JobVersion, job.entity_id) if job.entity_type == "job_version" else None
            )
            if job_version is not None and job_version.status == "processing":
                job_version.status = "draft"
            run = db.get(MatchRun, job.entity_id) if job.entity_type == "match_run" else None
            if run is not None and run.status == "processing":
                run.status = "queued"
            mark_blocked(db, job, "hosted_inference_not_configured")
        except InferenceProviderError:
            logger.warning("Hosted provider request failed for job %s", job.id)
            if job.job_type == "resume_extract":
                version = db.get(ResumeVersion, job.entity_id)
                if version is not None:
                    version.status = (
                        "queued"
                        if job.attempt_count < get_settings().worker_max_attempts
                        else "failed"
                    )
            elif job.job_type == "jd_analyze":
                version = db.get(JobVersion, job.entity_id)
                if version is not None:
                    version.status = (
                        "draft"
                        if job.attempt_count < get_settings().worker_max_attempts
                        else "failed"
                    )
            elif job.job_type == "match_run":
                run = db.get(MatchRun, job.entity_id)
                if run is not None:
                    run.status = (
                        "queued"
                        if job.attempt_count < get_settings().worker_max_attempts
                        else "failed"
                    )
            mark_failed(db, job, "hosted_provider_error")
        except Exception as exc:
            logger.error("Processing failed for job %s: %s", job.id, type(exc).__name__)
            if get_settings().environment == "testing":
                raise
            if job.job_type == "resume_extract":
                version = db.get(ResumeVersion, job.entity_id)
                if version is not None:
                    version.status = (
                        "queued"
                        if job.attempt_count < get_settings().worker_max_attempts
                        else "failed"
                    )
            elif job.job_type == "jd_analyze":
                version = db.get(JobVersion, job.entity_id)
                if version is not None:
                    version.status = (
                        "draft"
                        if job.attempt_count < get_settings().worker_max_attempts
                        else "failed"
                    )
            elif job.job_type == "match_run":
                run = db.get(MatchRun, job.entity_id)
                if run is not None:
                    run.status = (
                        "queued"
                        if job.attempt_count < get_settings().worker_max_attempts
                        else "failed"
                    )
            mark_failed(db, job, "processing_error")


async def consume(worker_index: int) -> None:
    worker_id = f"{uuid4().hex[:8]}-{worker_index}"
    while True:
        job_id = await asyncio.to_thread(claim_next_job, worker_id)
        if job_id is None:
            await asyncio.sleep(get_settings().worker_poll_seconds)
            continue
        await process_job(job_id)


async def run_worker() -> None:
    concurrency = max(1, get_settings().inference_max_concurrency)
    logger.info("Starting %s bounded workers", concurrency)
    await asyncio.gather(*(consume(index) for index in range(concurrency)))


if __name__ == "__main__":
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("Worker shutdown requested")
