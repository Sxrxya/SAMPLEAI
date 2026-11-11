from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_roles
from app.models import AuditEvent, Organization, ProcessingJob, User, Job, Resume, utc_now
from app.schemas import VerificationDecision
from app.services.queue import requeue_dead_letter

router = APIRouter(prefix="/admin", tags=["administration"])


@router.get("/metrics")
def get_admin_metrics(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    candidates_count = db.scalar(select(func.count(User.id)).where(User.role == "candidate")) or 0
    orgs_count = db.scalar(select(func.count(Organization.id))) or 0
    jobs_count = db.scalar(select(func.count(Job.id))) or 0
    resumes_count = db.scalar(select(func.count(Resume.id))) or 0
    return {
        "candidates": candidates_count,
        "recruiters": orgs_count,
        "jobs": jobs_count,
        "resumes": resumes_count,
    }


@router.get("/candidates")
def list_candidates(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    query = select(User).where(User.role == "candidate")
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    users = db.scalars(
        query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": u.id,
                "email": u.email,
                "display_name": u.display_name,
                "is_active": u.is_active,
                "created_at": u.created_at,
            }
            for u in users
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/recruiters")
def list_recruiters(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    query = select(Organization)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    orgs = db.scalars(
        query.order_by(Organization.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": o.id,
                "name": o.name,
                "status": o.status,
                "created_at": o.created_at,
            }
            for o in orgs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/jobs")
def list_admin_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    query = select(Job)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    jobs = db.scalars(
        query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": j.id,
                "organization_id": j.organization_id,
                "title": j.title,
                "location": j.location,
                "status": j.status,
                "created_at": j.created_at,
            }
            for j in jobs
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/ai-usage")
def get_ai_usage_summary(
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    total_jobs = db.scalar(select(func.count(ProcessingJob.id))) or 0
    succeeded_jobs = (
        db.scalar(select(func.count(ProcessingJob.id)).where(ProcessingJob.status == "succeeded")) or 0
    )
    failed_jobs = (
        db.scalar(select(func.count(ProcessingJob.id)).where(ProcessingJob.status == "failed")) or 0
    )
    return {
        "provider": "Hugging Face Inference API",
        "chat_model": "Qwen/Qwen2.5-72B-Instruct",
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "total_requests": total_jobs,
        "successful_requests": succeeded_jobs,
        "failed_requests": failed_jobs,
        "estimated_cost_usd": 0.00,  # Hugging Face Inference API is billed per token/plan, 0.00 local cost
        "status": "operational",
    }


@router.get("/processing/jobs")
def processing_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    query = select(ProcessingJob)
    if status_filter:
        query = query.where(ProcessingJob.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    jobs = db.scalars(
        query.order_by(ProcessingJob.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {
                "id": job.id,
                "entity_type": job.entity_type,
                "entity_id": job.entity_id,
                "job_type": job.job_type,
                "status": job.status,
                "attempt_count": job.attempt_count,
                "last_error_code": job.last_error_code,
                "created_at": job.created_at,
            }
            for job in jobs
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.post("/processing/jobs/{job_id}/retry")
def retry_processing_job(
    job_id: str,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    job = requeue_dead_letter(db, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Retryable processing job not found")
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="processing_job.requeued",
            entity_type="processing_job",
            entity_id=job.id,
        )
    )
    db.commit()
    return {"id": job.id, "status": job.status}


@router.get("/verifications")
def verification_queue(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    query = select(Organization).where(Organization.status == "pending_verification")
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    organizations = db.scalars(
        query.order_by(Organization.created_at).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [
            {"id": item.id, "name": item.name, "status": item.status} for item in organizations
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.patch("/verifications/{organization_id}")
def review_organization(
    organization_id: str,
    payload: VerificationDecision,
    admin: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
) -> dict:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if organization.status != "pending_verification":
        raise HTTPException(status_code=409, detail="Organization is not pending verification")
    organization.status = payload.decision
    db.add(
        AuditEvent(
            actor_id=admin.id,
            action="organization.verification_decided",
            entity_type="organization",
            entity_id=organization.id,
            metadata_json={
                "decision": payload.decision,
                "reason": payload.reason,
                "decided_at": utc_now().isoformat(),
            },
        )
    )
    db.commit()
    return {"id": organization.id, "status": organization.status}
