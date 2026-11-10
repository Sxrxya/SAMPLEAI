from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.db import get_db
from app.core.security import require_roles
from app.models import (
    Application,
    AuditEvent,
    Job,
    JobVersion,
    OrganizationMembership,
    Resume,
    ResumeConsent,
    ResumeVersion,
    User,
    utc_now,
)
from app.schemas import ApplicationCreate, ApplicationStatusUpdate

router = APIRouter(tags=["applications"])


@router.post("/candidate/jobs/{job_id}/applications", status_code=201)
def apply_to_job(
    job_id: str,
    payload: ApplicationCreate,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    job = db.scalar(select(Job).where(Job.id == job_id, Job.status == "active"))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    approved_job = db.scalar(
        select(JobVersion).where(JobVersion.job_id == job.id, JobVersion.status == "approved")
    )
    if approved_job is None:
        raise HTTPException(status_code=409, detail="Job is not approved")
    resume = db.scalar(
        select(ResumeVersion)
        .join(Resume, Resume.id == ResumeVersion.resume_id)
        .where(
            ResumeVersion.id == payload.resume_version_id,
            ResumeVersion.status == "complete",
            Resume.candidate_id == candidate.id,
        )
    )
    if resume is None:
        raise HTTPException(status_code=404, detail="Approved resume not found")
    scope = f"application:{job.organization_id}"
    consent = db.scalar(
        select(ResumeConsent).where(
            ResumeConsent.candidate_id == candidate.id,
            ResumeConsent.resume_version_id == resume.id,
            ResumeConsent.scope == scope,
            ResumeConsent.revoked_at.is_(None),
        )
    )
    if consent is None:
        consent = ResumeConsent(
            candidate_id=candidate.id,
            resume_version_id=resume.id,
            scope=scope,
        )
        db.add(consent)
        db.flush()
    application = Application(
        job_id=job.id,
        candidate_id=candidate.id,
        resume_version_id=resume.id,
        status="submitted",
    )
    db.add(application)
    db.flush()
    db.add(
        AuditEvent(
            actor_id=candidate.id,
            action="application.submitted",
            entity_type="application",
            entity_id=application.id,
            metadata_json={"job_id": job.id, "resume_version_id": resume.id},
        )
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An application already exists for this job"
        ) from exc
    return {"id": application.id, "job_id": job.id, "status": application.status}


@router.get("/candidate/applications")
def candidate_applications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    statement = (
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.candidate_id == candidate.id)
    )
    count_statement = select(Application.id).where(Application.candidate_id == candidate.id)
    if status_filter:
        statement = statement.where(Application.status == status_filter)
        count_statement = count_statement.where(Application.status == status_filter)
    total = db.scalar(select(func.count()).select_from(count_statement.subquery())) or 0
    rows = db.execute(
        statement.order_by(Application.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": application.id,
                "job_id": job.id,
                "title": job.title,
                "organization_id": job.organization_id,
                "status": application.status,
                "created_at": application.created_at,
            }
            for application, job in rows
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/candidate/applications/{application_id}")
def get_candidate_application(
    application_id: str,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    record = db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .where(Application.id == application_id, Application.candidate_id == candidate.id)
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application, job = record
    return {
        "id": application.id,
        "job_id": job.id,
        "title": job.title,
        "status": application.status,
        "created_at": application.created_at,
        "updated_at": application.updated_at,
    }


@router.post("/candidate/applications/{application_id}/withdraw")
def withdraw_candidate_application(
    application_id: str,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.candidate_id == candidate.id,
        )
    )
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    if application.status in {"rejected", "hired", "withdrawn"}:
        raise HTTPException(status_code=409, detail="Application is already in a terminal state")
    previous_status = application.status
    application.status = "withdrawn"
    application.updated_at = utc_now()
    db.add(
        AuditEvent(
            actor_id=candidate.id,
            action="application.withdrawn",
            entity_type="application",
            entity_id=application.id,
            metadata_json={"from": previous_status},
        )
    )
    db.commit()
    return {"id": application.id, "status": application.status}


@router.get("/recruiter/jobs/{job_id}/applicants")
def recruiter_applicants(
    job_id: str,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    membership = db.scalar(
        select(OrganizationMembership)
        .join(Job, Job.organization_id == OrganizationMembership.organization_id)
        .where(Job.id == job_id, OrganizationMembership.user_id == recruiter.id)
    )
    if membership is None:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = db.execute(
        select(Application, User, ResumeVersion)
        .join(User, User.id == Application.candidate_id)
        .join(ResumeVersion, ResumeVersion.id == Application.resume_version_id)
        .where(Application.job_id == job_id)
        .order_by(Application.created_at.desc())
    ).all()
    active_scopes = {
        consent.resume_version_id
        for consent in db.scalars(
            select(ResumeConsent).where(
                ResumeConsent.scope == f"application:{membership.organization_id}",
                ResumeConsent.revoked_at.is_(None),
            )
        ).all()
    }
    return {
        "items": [
            {
                "application_id": application.id,
                "candidate_id": user.id,
                "name": user.display_name,
                "resume_version_id": resume.id,
                "resume_version": resume.version_number,
                "status": application.status,
                "created_at": application.created_at,
            }
            for application, user, resume in rows
            if resume.id in active_scopes
        ],
        "page": 1,
        "page_size": len(rows),
        "total": len(rows),
        "pages": 1 if rows else 0,
    }


@router.patch("/recruiter/applications/{application_id}/status")
def update_application_status(
    application_id: str,
    payload: ApplicationStatusUpdate,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    record = db.execute(
        select(Application, Job)
        .join(Job, Job.id == Application.job_id)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Job.organization_id,
        )
        .where(
            Application.id == application_id,
            OrganizationMembership.user_id == recruiter.id,
        )
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application, _job = record
    if application.status in {"rejected", "hired", "withdrawn"}:
        raise HTTPException(status_code=409, detail="Application is already in a terminal state")
    previous_status = application.status
    application.status = payload.status
    application.updated_at = utc_now()
    db.add(
        AuditEvent(
            actor_id=recruiter.id,
            action="application.status_changed",
            entity_type="application",
            entity_id=application.id,
            metadata_json={
                "from": previous_status,
                "to": payload.status,
                "reason": payload.reason,
            },
        )
    )
    db.commit()
    return {"id": application.id, "status": application.status}


@router.get("/recruiter/applications/{application_id}/resume")
def recruiter_application_resume(
    application_id: str,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> FileResponse:
    record = db.execute(
        select(Application, Job, ResumeVersion)
        .join(Job, Job.id == Application.job_id)
        .join(ResumeVersion, ResumeVersion.id == Application.resume_version_id)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Job.organization_id,
        )
        .where(
            Application.id == application_id,
            OrganizationMembership.user_id == recruiter.id,
        )
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Application not found")
    application, job, resume = record
    consent = db.scalar(
        select(ResumeConsent.id).where(
            ResumeConsent.resume_version_id == resume.id,
            ResumeConsent.candidate_id == application.candidate_id,
            ResumeConsent.scope == f"application:{job.organization_id}",
            ResumeConsent.revoked_at.is_(None),
        )
    )
    if consent is None:
        raise HTTPException(status_code=403, detail="Candidate sharing consent is not active")
    root = get_settings().storage_root.resolve()
    path = (root / resume.storage_key).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file is unavailable")
    return FileResponse(
        path,
        filename=resume.original_filename,
        media_type=resume.mime_type,
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store"},
    )
