from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import engine
from app.models import ProcessingJob, new_id, utc_now


def enqueue_job(
    db: Session,
    *,
    entity_type: str,
    entity_id: str,
    job_type: str,
    idempotency_key: str,
) -> ProcessingJob:
    now = utc_now()
    db.execute(
        sqlite_insert(ProcessingJob)
        .values(
            id=new_id(),
            entity_type=entity_type,
            entity_id=entity_id,
            job_type=job_type,
            status="queued",
            attempt_count=0,
            available_at=now,
            locked_until=None,
            worker_id=None,
            idempotency_key=idempotency_key,
            last_error_code=None,
            created_at=now,
            updated_at=now,
        )
        .on_conflict_do_nothing(index_elements=["idempotency_key"])
    )
    return db.scalar(select(ProcessingJob).where(ProcessingJob.idempotency_key == idempotency_key))


def claim_next_job(worker_id: str | None = None) -> str | None:
    now = utc_now()
    settings = get_settings()
    token = worker_id or uuid4().hex
    statement = text(
        """
        UPDATE processing_jobs
        SET status = 'processing', worker_id = :worker_id,
            locked_until = :locked_until, attempt_count = attempt_count + 1,
            updated_at = :now
        WHERE id = (
            SELECT id FROM processing_jobs
            WHERE (status IN ('queued', 'retry_wait') AND available_at <= :now)
               OR (status = 'processing' AND locked_until <= :now)
            ORDER BY available_at, created_at
            LIMIT 1
        )
        AND ((status IN ('queued', 'retry_wait') AND available_at <= :now)
             OR (status = 'processing' AND locked_until <= :now))
        RETURNING id
        """
    )
    with engine.begin() as connection:
        result = connection.execute(
            statement,
            {
                "worker_id": token,
                "locked_until": now + timedelta(seconds=settings.worker_lease_seconds),
                "now": now,
            },
        ).scalar_one_or_none()
    return result


def mark_succeeded(db: Session, job: ProcessingJob) -> None:
    job.status = "succeeded"
    job.locked_until = None
    job.worker_id = None
    job.last_error_code = None
    db.commit()


def mark_failed(db: Session, job: ProcessingJob, error_code: str) -> None:
    settings = get_settings()
    job.locked_until = None
    job.worker_id = None
    job.last_error_code = error_code[:80]
    if job.attempt_count >= settings.worker_max_attempts:
        job.status = "dead_letter"
    else:
        delay = min(60 * 2 ** (job.attempt_count - 1), 3600)
        job.status = "retry_wait"
        job.available_at = utc_now() + timedelta(seconds=delay)
    db.commit()


def mark_blocked(db: Session, job: ProcessingJob, error_code: str) -> None:
    job.status = "blocked"
    job.locked_until = None
    job.worker_id = None
    job.last_error_code = error_code[:80]
    db.commit()


def requeue_dead_letter(db: Session, job_id: str) -> ProcessingJob | None:
    job = db.scalar(select(ProcessingJob).where(ProcessingJob.id == job_id))
    if job is None or job.status not in {"dead_letter", "blocked"}:
        return None
    job.status = "queued"
    job.attempt_count = 0
    job.available_at = utc_now()
    job.last_error_code = None
    db.commit()
    db.refresh(job)
    return job
