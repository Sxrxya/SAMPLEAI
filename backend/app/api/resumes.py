from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import require_roles
from app.models import (
    AuditEvent,
    ProcessingJob,
    Resume,
    ResumeConsent,
    ResumeExtraction,
    ResumeVersion,
    User,
    utc_now,
)
from app.schemas import (
    ConsentRequest,
    ProcessingStatusResponse,
    ResumeExtractionPayload,
    ResumeReviewRequest,
    ResumeUploadResponse,
)
from app.services.documents import store_upload
from app.services.queue import enqueue_job
from app.services.search import upsert_resume_search

router = APIRouter(prefix="/candidate/resumes", tags=["candidate resumes"])


def _owned_version(db: Session, candidate_id: str, version_id: str) -> ResumeVersion:
    version = db.scalar(
        select(ResumeVersion)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(ResumeVersion.id == version_id, Resume.candidate_id == candidate_id)
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return version


def _upload_response(version: ResumeVersion, processing_job_id: str | None) -> ResumeUploadResponse:
    return ResumeUploadResponse(
        resume_id=version.resume_id,
        resume_version_id=version.id,
        processing_job_id=processing_job_id,
        status=version.status,
    )


@router.post("", response_model=ResumeUploadResponse, status_code=202)
async def upload_resume(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    consent_to_ai_processing: bool = Form(...),
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> ResumeUploadResponse:
    key = f"resume-upload:{candidate.id}:{idempotency_header or uuid4().hex}"[:128]
    existing_job = db.scalar(select(ProcessingJob).where(ProcessingJob.idempotency_key == key))
    if existing_job is not None:
        version = _owned_version(db, candidate.id, existing_job.entity_id)
        return _upload_response(version, existing_job.id)
    existing_version = db.scalar(
        select(ResumeVersion)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(
            Resume.candidate_id == candidate.id,
            ResumeVersion.upload_idempotency_key == key,
        )
    )
    if existing_version is not None:
        return _upload_response(existing_version, None)

    settings = get_settings()
    storage_key = ""
    try:
        storage_key, filename, byte_size, sha256, extension = await store_upload(file, candidate.id)
        resume = db.scalar(
            select(Resume)
            .where(Resume.candidate_id == candidate.id)
            .order_by(Resume.created_at.desc())
        )
        if resume is None:
            resume = Resume(candidate_id=candidate.id)
            db.add(resume)
            db.flush()

        duplicate = db.scalar(
            select(ResumeVersion)
            .join(Resume)
            .where(Resume.candidate_id == candidate.id, ResumeVersion.source_sha256 == sha256)
        )
        if duplicate is not None:
            (settings.storage_root / storage_key).unlink(missing_ok=True)
            job = db.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.entity_type == "resume_version",
                    ProcessingJob.entity_id == duplicate.id,
                    ProcessingJob.job_type == "resume_extract",
                )
            )
            return _upload_response(duplicate, job.id if job else None)

        latest_version = db.scalar(
            select(func.max(ResumeVersion.version_number)).where(
                ResumeVersion.resume_id == resume.id
            )
        )
        version = ResumeVersion(
            resume_id=resume.id,
            version_number=(latest_version or 0) + 1,
            original_filename=filename,
            storage_key=storage_key,
            mime_type=file.content_type or "application/octet-stream",
            byte_size=byte_size,
            source_sha256=sha256,
            status="queued" if consent_to_ai_processing else "needs_consent",
            upload_idempotency_key=key,
        )
        db.add(version)
        db.flush()
        processing_job_id = None
        if consent_to_ai_processing:
            db.add(
                ResumeConsent(
                    candidate_id=candidate.id,
                    resume_version_id=version.id,
                    scope="ai_processing",
                )
            )
            processing_job = enqueue_job(
                db,
                entity_type="resume_version",
                entity_id=version.id,
                job_type="resume_extract",
                idempotency_key=key,
            )
            if processing_job.entity_id != version.id:
                db.rollback()
                (settings.storage_root / storage_key).unlink(missing_ok=True)
                existing = db.scalar(
                    select(ResumeVersion).where(ResumeVersion.id == processing_job.entity_id)
                )
                if existing is None:
                    raise HTTPException(
                        status_code=409, detail="Idempotent upload is being committed"
                    )
                return _upload_response(existing, processing_job.id)
            processing_job_id = processing_job.id
        db.add(
            AuditEvent(
                actor_id=candidate.id,
                action="resume.uploaded",
                entity_type="resume_version",
                entity_id=version.id,
                metadata_json={"sha256": sha256, "extension": extension},
            )
        )
        db.commit()
        db.refresh(version)

        # Trigger extraction immediately via background tasks so it processes automatically
        if processing_job_id:
            from app.worker import process_job
            background_tasks.add_task(process_job, processing_job_id)

        return _upload_response(version, processing_job_id)
    except IntegrityError:
        db.rollback()
        if storage_key:
            (settings.storage_root / storage_key).unlink(missing_ok=True)
        existing_version = db.scalar(
            select(ResumeVersion)
            .join(Resume, Resume.id == ResumeVersion.resume_id)
            .where(
                Resume.candidate_id == candidate.id,
                ResumeVersion.upload_idempotency_key == key,
            )
        )
        if existing_version is not None:
            processing_job = db.scalar(
                select(ProcessingJob).where(
                    ProcessingJob.entity_type == "resume_version",
                    ProcessingJob.entity_id == existing_version.id,
                    ProcessingJob.job_type == "resume_extract",
                )
            )
            return _upload_response(existing_version, processing_job.id if processing_job else None)
        raise HTTPException(
            status_code=409, detail="Resume upload conflicts with an existing record"
        ) from None
    except Exception:
        db.rollback()
        if storage_key:
            (settings.storage_root / storage_key).unlink(missing_ok=True)
        raise


@router.get("/{resume_version_id}/status", response_model=ProcessingStatusResponse)
def resume_status(
    resume_version_id: str,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> ProcessingStatusResponse:
    version = _owned_version(db, candidate.id, resume_version_id)
    job = db.scalar(
        select(ProcessingJob)
        .where(
            ProcessingJob.entity_type == "resume_version",
            ProcessingJob.entity_id == version.id,
            ProcessingJob.job_type == "resume_extract",
        )
        .order_by(ProcessingJob.created_at.desc())
    )
    return ProcessingStatusResponse(
        id=job.id if job else version.id,
        status=(
            "blocked"
            if job and job.status == "blocked"
            else "failed"
            if job and job.status == "dead_letter"
            else version.status
        ),
        attempt_count=job.attempt_count if job else 0,
        last_error_code=job.last_error_code if job else None,
        created_at=job.created_at if job else version.created_at,
    )


@router.post("/{resume_version_id}/processing-consent")
def update_processing_consent(
    resume_version_id: str,
    payload: ConsentRequest,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    version = _owned_version(db, candidate.id, resume_version_id)
    current = db.scalar(
        select(ResumeConsent).where(
            ResumeConsent.resume_version_id == version.id,
            ResumeConsent.scope == "ai_processing",
            ResumeConsent.revoked_at.is_(None),
        )
    )
    if payload.consent:
        if current is None:
            db.add(
                ResumeConsent(
                    candidate_id=candidate.id,
                    resume_version_id=version.id,
                    scope="ai_processing",
                )
            )
        if version.status in {"needs_consent", "failed"}:
            version.status = "queued"
            enqueue_job(
                db,
                entity_type="resume_version",
                entity_id=version.id,
                job_type="resume_extract",
                idempotency_key=f"resume-processing:{version.id}:{uuid4().hex}"[:128],
            )
    else:
        if version.status == "processing":
            raise HTTPException(status_code=409, detail="Processing is already in progress")
        if current is not None:
            current.revoked_at = utc_now()
        if version.status == "queued":
            version.status = "needs_consent"
    db.add(
        AuditEvent(
            actor_id=candidate.id,
            action="resume.processing_consent_changed",
            entity_type="resume_version",
            entity_id=version.id,
            metadata_json={"consent": payload.consent},
        )
    )
    db.commit()
    return {"resume_version_id": version.id, "consent_to_ai_processing": payload.consent}


@router.get("/{resume_version_id}/extracted", response_model=ResumeExtractionPayload)
def get_extraction(
    resume_version_id: str,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> ResumeExtractionPayload:
    version = _owned_version(db, candidate.id, resume_version_id)
    extraction = db.scalar(
        select(ResumeExtraction)
        .where(ResumeExtraction.resume_version_id == version.id)
        .order_by(ResumeExtraction.created_at.desc())
    )
    if extraction is None:
        raise HTTPException(status_code=409, detail="Resume extraction is not ready")
    return ResumeExtractionPayload.model_validate(extraction.extraction_json)


@router.put("/{resume_version_id}/extracted", response_model=ResumeExtractionPayload)
def review_extraction(
    resume_version_id: str,
    payload: ResumeReviewRequest,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> ResumeExtractionPayload:
    if not payload.confirmed:
        raise HTTPException(status_code=422, detail="Candidate confirmation is required")
    version = _owned_version(db, candidate.id, resume_version_id)
    extraction = db.scalar(
        select(ResumeExtraction)
        .where(ResumeExtraction.resume_version_id == version.id)
        .order_by(ResumeExtraction.created_at.desc())
    )
    if extraction is None or version.status != "needs_review":
        raise HTTPException(status_code=409, detail="Resume is not awaiting review")
    extraction.extraction_json = payload.extraction.model_dump(mode="json")
    extraction.review_status = "confirmed"
    version.status = "complete"
    db.add(
        AuditEvent(
            actor_id=candidate.id,
            action="resume.extraction_reviewed",
            entity_type="resume_version",
            entity_id=version.id,
        )
    )
    db.flush()
    has_sharing_consent = db.scalar(
        select(ResumeConsent.id).where(
            ResumeConsent.resume_version_id == version.id,
            ResumeConsent.scope == "recruiter_search",
            ResumeConsent.revoked_at.is_(None),
        )
    )
    if has_sharing_consent:
        upsert_resume_search(
            db,
            resume_version_id=version.id,
            candidate_id=candidate.id,
            searchable_text=payload.extraction.model_dump_json(),
        )
    db.commit()
    return payload.extraction


@router.patch("/{resume_version_id}/consent")
def update_sharing_consent(
    resume_version_id: str,
    payload: ConsentRequest,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    version = _owned_version(db, candidate.id, resume_version_id)
    if payload.consent and version.status != "complete":
        raise HTTPException(status_code=409, detail="Review the resume before sharing it")
    active_consents = db.scalars(
        select(ResumeConsent).where(
            ResumeConsent.resume_version_id == version.id,
            ResumeConsent.scope == "recruiter_search",
            ResumeConsent.revoked_at.is_(None),
        )
    ).all()
    if payload.consent and not active_consents:
        db.add(
            ResumeConsent(
                candidate_id=candidate.id,
                resume_version_id=version.id,
                scope="recruiter_search",
            )
        )
        extraction = db.scalar(
            select(ResumeExtraction)
            .where(ResumeExtraction.resume_version_id == version.id)
            .order_by(ResumeExtraction.created_at.desc())
        )
        if extraction:
            upsert_resume_search(
                db,
                resume_version_id=version.id,
                candidate_id=candidate.id,
                searchable_text=ResumeExtractionPayload.model_validate(
                    extraction.extraction_json
                ).model_dump_json(),
            )
    elif not payload.consent:
        for consent in active_consents:
            consent.revoked_at = utc_now()
        db.execute(
            text("DELETE FROM resume_search WHERE resume_version_id = :resume_id"),
            {"resume_id": version.id},
        )
    db.add(
        AuditEvent(
            actor_id=candidate.id,
            action="resume.sharing_consent_changed",
            entity_type="resume_version",
            entity_id=version.id,
            metadata_json={"consent": payload.consent},
        )
    )
    db.commit()
    return {"resume_version_id": version.id, "consent": payload.consent}


@router.get("/{resume_version_id}/file")
def download_resume(
    resume_version_id: str,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> FileResponse:
    version = _owned_version(db, candidate.id, resume_version_id)
    root = get_settings().storage_root.resolve()
    path = (root / version.storage_key).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file is unavailable")
    return FileResponse(
        path,
        filename=version.original_filename,
        media_type=version.mime_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )
