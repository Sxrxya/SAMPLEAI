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
    extraction, actual_model_id = await inference.extract_resume(source_text)
    db.add(
        ResumeExtraction(
            resume_version_id=version.id,
            schema_version=extraction.schema_version,
            prompt_version="resume-extraction-v1",
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
    run = db.get(MatchRun, job.entity_id)
    if run is None:
        raise ValueError("match run not found")
    job_version = db.get(JobVersion, run.job_version_id)
    if job_version is None or job_version.status != "approved":
        raise ValueError("approved job description not found")
    run.status = "processing"
    db.commit()

    analysis = JobExtractionPayload.model_validate(job_version.analysis_json or {})
    query = " ".join(
        [
            analysis.role_title,
            *(requirement.description for requirement in analysis.required_skills),
            *(requirement.description for requirement in analysis.preferred_skills),
            *(requirement.description for requirement in analysis.experience_requirements),
            job_version.description[:3000],
        ]
    )
    candidates_by_version = {
        item["resume_version_id"]: item for item in eligible_resume_search(db, query, limit=250)
    }
    required_skills = {
        _normalize_skill(item.requirement_key.removeprefix("required:"))
        for item in db.scalars(
            select(JobRequirement).where(
                JobRequirement.job_version_id == job_version.id,
                JobRequirement.requirement_type == "required",
            )
        ).all()
        if item.requirement_key
    }
    db.commit()

    query_vector: list[float] | None = None
    embedding_model_id = ""
    if get_settings().inference_enabled:
        try:
            query_vector, embedding_model_id = await inference.embed(job_version.description)
        except (InferenceUnavailable, InferenceProviderError):
            logger.warning("Semantic retrieval unavailable for match run %s", run.id)

    vector_candidates: dict[str, list[float]] = {}
    if query_vector is not None:
        for item in eligible_resume_embeddings(db, embedding_model_id):
            version_id = item["resume_version_id"]
            candidates_by_version.setdefault(
                version_id,
                {"resume_version_id": version_id, "candidate_id": item["candidate_id"]},
            )
            vector_candidates[version_id] = item["vector_json"]

    scored: list[tuple[dict, float | None]] = []
    for candidate in candidates_by_version.values():
        score = None
        candidate_vector = vector_candidates.get(candidate["resume_version_id"])
        if query_vector is not None and candidate_vector is not None:
            score = cosine_similarity(query_vector, candidate_vector)
        scored.append((candidate, score))

    if any(score is not None for _, score in scored):
        scored.sort(key=lambda pair: pair[1] if pair[1] is not None else -1, reverse=True)

    for rank, (candidate, score) in enumerate(scored[: run.top_k], start=1):
        extraction_record = db.scalar(
            select(ResumeExtraction)
            .where(ResumeExtraction.resume_version_id == candidate["resume_version_id"])
            .order_by(ResumeExtraction.created_at.desc())
        )
        if extraction_record is None:
            continue
        extraction = ResumeExtractionPayload.model_validate(extraction_record.extraction_json)
        candidate_skills = {_normalize_skill(item.name) for item in extraction.skills}
        missing = sorted(required_skills - candidate_skills)
        evidence = [
            {
                "dimension": "required_skills",
                "skill": skill.name,
                "evidence": [item.model_dump(mode="json") for item in skill.evidence],
            }
            for skill in extraction.skills
            if _normalize_skill(skill.name) in required_skills and skill.evidence
        ]
        db.add(
            MatchResult(
                match_run_id=run.id,
                candidate_id=candidate["candidate_id"],
                resume_version_id=candidate["resume_version_id"],
                rank=rank,
                retrieval_method=(
                    "fts5+cosine"
                    if score is not None and candidate["resume_version_id"] in vector_candidates
                    else "cosine"
                    if score is not None
                    else "fts5"
                ),
                relevance_score=score,
                dimensions_json={
                    "semantic_similarity": score,
                    "required_skills": {
                        "matched": sorted(required_skills & candidate_skills),
                        "missing": missing,
                    },
                },
                missing_requirements_json=missing,
                evidence_json=evidence,
            )
        )
    run.status = "complete"
    mark_succeeded(db, job)


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
