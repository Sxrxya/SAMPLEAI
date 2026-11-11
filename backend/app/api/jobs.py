from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import require_roles
from app.models import (
    AuditEvent,
    Job,
    JobRequirement,
    JobVersion,
    MatchResult,
    MatchRun,
    Organization,
    OrganizationMembership,
    ProcessingJob,
    User,
    utc_now,
)
from app.schemas import (
    JobCreate,
    JobCreateResponse,
    JobReviewRequest,
    MatchResultResponse,
    MatchRunRequest,
    StrictModel,
)
from app.services.matching import execute_job_matching
from app.services.queue import enqueue_job

router = APIRouter(tags=["jobs and matching"])


def _organization_job(
    db: Session, recruiter_id: str, job_id: str
) -> tuple[Job, OrganizationMembership]:
    record = db.execute(
        select(Job, OrganizationMembership)
        .join(
            OrganizationMembership,
            OrganizationMembership.organization_id == Job.organization_id,
        )
        .where(Job.id == job_id, OrganizationMembership.user_id == recruiter_id)
    ).first()
    if record is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return record[0], record[1]


@router.post("/employer/jobs", response_model=JobCreateResponse, status_code=202)
def create_job(
    payload: JobCreate,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> JobCreateResponse:
    key = f"jd-analysis:{recruiter.id}:{idempotency_header or uuid4().hex}"[:128]
    existing_job = db.scalar(select(ProcessingJob).where(ProcessingJob.idempotency_key == key))
    if existing_job is not None:
        version = db.get(JobVersion, existing_job.entity_id)
        job = db.get(Job, version.job_id) if version else None
        if job and version:
            return JobCreateResponse(
                id=job.id,
                version_id=version.id,
                status=version.status,
                analysis_job_id=existing_job.id,
            )

    membership = db.scalar(
        select(OrganizationMembership).where(OrganizationMembership.user_id == recruiter.id)
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Recruiter has no organization")
    job = Job(
        organization_id=membership.organization_id,
        created_by=recruiter.id,
        title=payload.title.strip(),
        location=payload.location,
        status="draft",
    )
    db.add(job)
    db.flush()
    version = JobVersion(job_id=job.id, version_number=1, description=payload.description)
    db.add(version)
    db.flush()
    processing_job = enqueue_job(
        db,
        entity_type="job_version",
        entity_id=version.id,
        job_type="jd_analyze",
        idempotency_key=key,
    )
    if processing_job.entity_id != version.id:
        existing_version = db.get(JobVersion, processing_job.entity_id)
        existing_job = db.get(Job, existing_version.job_id) if existing_version else None
        db.rollback()
        if existing_version is not None and existing_job is not None:
            return JobCreateResponse(
                id=existing_job.id,
                version_id=existing_version.id,
                status=existing_version.status,
                analysis_job_id=processing_job.id,
            )
        raise HTTPException(status_code=409, detail="Idempotent job request is being committed")
    db.add(
        AuditEvent(
            actor_id=recruiter.id,
            action="job.draft_created",
            entity_type="job",
            entity_id=job.id,
        )
    )
    db.commit()
    return JobCreateResponse(
        id=job.id,
        version_id=version.id,
        status=version.status,
        analysis_job_id=processing_job.id,
    )


@router.get("/employer/jobs")
def list_employer_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    organization_ids = select(OrganizationMembership.organization_id).where(
        OrganizationMembership.user_id == recruiter.id
    )
    total = (
        db.scalar(select(func.count(Job.id)).where(Job.organization_id.in_(organization_ids))) or 0
    )
    jobs = db.scalars(
        select(Job)
        .where(Job.organization_id.in_(organization_ids))
        .order_by(Job.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return {
        "items": [
            {"id": job.id, "title": job.title, "location": job.location, "status": job.status}
            for job in jobs
        ],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/candidate/jobs")
def list_candidate_jobs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = None,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    del candidate
    query = select(Job).where(Job.status == "active")
    if search:
        query = query.where(Job.title.ilike(f"%{search[:100]}%"))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    jobs = db.scalars(
        query.order_by(Job.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return {
        "items": [{"id": job.id, "title": job.title, "location": job.location} for job in jobs],
        "page": page,
        "page_size": page_size,
        "total": total,
        "pages": (total + page_size - 1) // page_size,
    }


@router.get("/candidate/jobs/{job_id}")
def get_candidate_job(
    job_id: str,
    candidate: User = Depends(require_roles("candidate")),
    db: Session = Depends(get_db),
) -> dict:
    del candidate
    job = db.scalar(select(Job).where(Job.id == job_id, Job.status == "active"))
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    organization = db.get(Organization, job.organization_id)
    version = db.scalar(
        select(JobVersion).where(JobVersion.job_id == job.id, JobVersion.status == "approved")
    )
    requirements = (
        db.scalars(select(JobRequirement).where(JobRequirement.job_version_id == version.id)).all()
        if version
        else []
    )
    return {
        "id": job.id,
        "title": job.title,
        "location": job.location,
        "organization": organization.name if organization else None,
        "description": version.description if version else "",
        "requirements": [
            {
                "type": item.requirement_type,
                "description": item.description,
                "evidence": item.evidence,
            }
            for item in requirements
        ],
    }


@router.get("/employer/jobs/{job_id}/description")
def get_job_description(
    job_id: str,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    job, _ = _organization_job(db, recruiter.id, job_id)
    version = db.scalar(
        select(JobVersion)
        .where(JobVersion.job_id == job.id)
        .order_by(JobVersion.version_number.desc())
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Job description not found")
    return {
        "job_id": job.id,
        "job_version_id": version.id,
        "description": version.description,
        "status": version.status,
        "analysis": version.analysis_json,
    }


@router.put("/employer/jobs/{job_id}/description")
def review_job_requirements(
    job_id: str,
    payload: JobReviewRequest,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    job, _ = _organization_job(db, recruiter.id, job_id)
    version = db.scalar(
        select(JobVersion)
        .where(JobVersion.job_id == job.id)
        .order_by(JobVersion.version_number.desc())
    )
    if version is None or version.status != "needs_review":
        raise HTTPException(status_code=409, detail="JD analysis is not ready for review")
    version.analysis_json = payload.extraction.model_dump(mode="json")
    version.status = "reviewed"
    db.execute(delete(JobRequirement).where(JobRequirement.job_version_id == version.id))
    requirements = [
        *payload.extraction.required_skills,
        *payload.extraction.preferred_skills,
        *payload.extraction.experience_requirements,
        *payload.extraction.education_requirements,
    ]
    db.add_all(
        [
            JobRequirement(
                job_version_id=version.id,
                requirement_key=f"{requirement.requirement_type}:{requirement.key}",
                requirement_type=requirement.requirement_type,
                description=requirement.description,
                evidence=[item.model_dump(mode="json") for item in requirement.evidence],
            )
            for requirement in requirements
        ]
    )
    db.add(
        AuditEvent(
            actor_id=recruiter.id,
            action="job.requirements_reviewed",
            entity_type="job_version",
            entity_id=version.id,
        )
    )
    db.commit()
    return {"job_id": job.id, "job_version_id": version.id, "status": version.status}


@router.post("/employer/jobs/{job_id}/approve")
def approve_job(
    job_id: str,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    job, membership = _organization_job(db, recruiter.id, job_id)
    version = db.scalar(
        select(JobVersion)
        .where(JobVersion.job_id == job.id)
        .order_by(JobVersion.version_number.desc())
    )
    organization = db.get(Organization, membership.organization_id)
    if version is None or version.status != "reviewed":
        raise HTTPException(status_code=409, detail="Review extracted requirements before approval")
    if organization is None or organization.status != "verified":
        raise HTTPException(
            status_code=403, detail="Organization must be verified before publishing"
        )
    version.status = "approved"
    version.approved_at = utc_now()
    job.status = "active"
    db.add(
        AuditEvent(
            actor_id=recruiter.id,
            action="job.published",
            entity_type="job",
            entity_id=job.id,
        )
    )
    db.commit()
    return {"job_id": job.id, "job_version_id": version.id, "status": job.status}


@router.post("/recruiter/jobs/{job_id}/match-runs", status_code=202)
def create_match_run(
    job_id: str,
    payload: MatchRunRequest,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
    idempotency_header: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    job, _ = _organization_job(db, recruiter.id, job_id)
    version = db.scalar(
        select(JobVersion)
        .where(JobVersion.job_id == job.id, JobVersion.status == "approved")
        .order_by(JobVersion.version_number.desc())
    )
    if version is None:
        raise HTTPException(status_code=409, detail="An approved JD is required before matching")
    key = f"match-run:{recruiter.id}:{idempotency_header or uuid4().hex}"[:128]
    existing = db.scalar(select(ProcessingJob).where(ProcessingJob.idempotency_key == key))
    if existing is not None:
        return {"match_run_id": existing.entity_id, "processing_job_id": existing.id}
    run = MatchRun(
        job_version_id=version.id,
        requested_by=recruiter.id,
        top_k=payload.top_k,
        config_version="fts5-cosine-v1",
    )
    db.add(run)
    db.flush()
    processing_job = enqueue_job(
        db,
        entity_type="match_run",
        entity_id=run.id,
        job_type="match_run",
        idempotency_key=key,
    )
    db.add(
        AuditEvent(
            actor_id=recruiter.id,
            action="matching.run_created",
            entity_type="match_run",
            entity_id=run.id,
        )
    )
    db.commit()
    return {"match_run_id": run.id, "processing_job_id": processing_job.id}


@router.get("/recruiter/match-runs/{run_id}")
def get_match_run(
    run_id: str,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    run = db.get(MatchRun, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Match run not found")
    job_version = db.get(JobVersion, run.job_version_id)
    job = db.get(Job, job_version.job_id) if job_version else None
    if job is None:
        raise HTTPException(status_code=404, detail="Match run not found")
    _organization_job(db, recruiter.id, job.id)
    results = db.scalars(
        select(MatchResult).where(MatchResult.match_run_id == run.id).order_by(MatchResult.rank)
    ).all()
    return {
        "id": run.id,
        "status": run.status,
        "job_id": job.id,
        "job_version_id": run.job_version_id,
        "results": [
            MatchResultResponse(
                rank=result.rank,
                candidate_id=result.candidate_id,
                resume_version_id=result.resume_version_id,
                retrieval_method=result.retrieval_method,
                relevance_score=result.relevance_score,
                dimensions=result.dimensions_json,
                missing_requirements=result.missing_requirements_json,
                evidence=result.evidence_json,
            ).model_dump()
            for result in results
        ],
    }


@router.get("/recruiter/jobs/{job_id}/matches")
async def get_job_matches(
    job_id: str,
    top_k: int = Query(default=5, ge=1, le=10),
    refresh: bool = Query(default=False),
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    job, _ = _organization_job(db, recruiter.id, job_id)
    matches = await execute_job_matching(
        db=db,
        job_id=job.id,
        top_k=top_k,
        recruiter_id=recruiter.id,
    )
    return {
        "job_id": job.id,
        "job_title": job.title,
        "location": job.location,
        "items": matches,
        "total": len(matches),
    }


@router.post("/recruiter/jobs/{job_id}/matches/run")
async def trigger_job_matches(
    job_id: str,
    top_k: int = Query(default=5, ge=1, le=10),
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    job, _ = _organization_job(db, recruiter.id, job_id)
    matches = await execute_job_matching(
        db=db,
        job_id=job.id,
        top_k=top_k,
        recruiter_id=recruiter.id,
    )
    return {
        "job_id": job.id,
        "job_title": job.title,
        "items": matches,
        "total": len(matches),
    }


@router.get("/recruiter/jobs/{job_id}/matches/{candidate_id}/evidence")
def get_candidate_match_evidence(
    job_id: str,
    candidate_id: str,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    job, _ = _organization_job(db, recruiter.id, job_id)
    result = db.scalar(
        select(MatchResult)
        .join(MatchRun, MatchRun.id == MatchResult.match_run_id)
        .join(JobVersion, JobVersion.id == MatchRun.job_version_id)
        .where(
            JobVersion.job_id == job.id,
            MatchResult.candidate_id == candidate_id,
        )
        .order_by(MatchResult.created_at.desc())
    )
    if result is None:
        raise HTTPException(status_code=404, detail="Evidence not found for candidate")
    return {
        "candidate_id": candidate_id,
        "job_id": job.id,
        "rank": result.rank,
        "relevance_score": result.relevance_score,
        "dimensions": result.dimensions_json,
        "missing_requirements": result.missing_requirements_json,
        "evidence": result.evidence_json,
    }


class QuickMatchRequest(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20, max_length=30000)
    location: str | None = Field(default=None, max_length=160)
    top_k: int = Field(default=5, ge=1, le=10)


@router.post("/employer/jobs/quick-match")
async def quick_match_jd(
    payload: QuickMatchRequest,
    recruiter: User = Depends(require_roles("recruiter")),
    db: Session = Depends(get_db),
) -> dict:
    membership = db.scalar(
        select(OrganizationMembership).where(OrganizationMembership.user_id == recruiter.id)
    )
    if membership is None:
        raise HTTPException(status_code=403, detail="Recruiter has no organization")

    job = Job(
        organization_id=membership.organization_id,
        created_by=recruiter.id,
        title=payload.title.strip(),
        location=payload.location,
        status="active",
    )
    db.add(job)
    db.flush()

    version = JobVersion(
        job_id=job.id,
        version_number=1,
        description=payload.description,
        status="approved",
        approved_at=utc_now(),
    )
    db.add(version)
    db.commit()

    matches = await execute_job_matching(
        db=db,
        job_id=job.id,
        top_k=payload.top_k,
        recruiter_id=recruiter.id,
    )
    return {
        "job_id": job.id,
        "title": job.title,
        "location": job.location,
        "items": matches,
        "total": len(matches),
    }
