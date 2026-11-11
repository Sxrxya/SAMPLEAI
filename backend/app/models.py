from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.core.db import Base


def new_id() -> str:
    return str(uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role IN ('candidate', 'recruiter', 'admin')"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    display_name: Mapped[str] = mapped_column(String(160))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="candidate")
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    __table_args__ = (Index("ix_auth_sessions_user_expiry", "user_id", "expires_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    expires_at: Mapped[datetime]
    revoked_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    headline: Mapped[str | None] = mapped_column(String(240))
    location: Mapped[str | None] = mapped_column(String(160))
    preferences_json: Mapped[dict] = mapped_column(JSON, default=dict)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(24), default="pending_verification")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class OrganizationMembership(Base):
    __tablename__ = "organization_memberships"
    __table_args__ = (UniqueConstraint("organization_id", "user_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(24), default="recruiter")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    canonical_name: Mapped[str] = mapped_column(String(120), unique=True, index=True)


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"
    __table_args__ = (UniqueConstraint("candidate_id", "skill_id"),)

    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[str] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency: Mapped[str | None] = mapped_column(String(24))
    evidence: Mapped[str | None] = mapped_column(Text)


class Resume(Base):
    __tablename__ = "resumes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number"),
        UniqueConstraint("resume_id", "source_sha256"),
        CheckConstraint(
            "status IN ('needs_consent', 'queued', 'processing', 'needs_review', "
            "'complete', 'failed')"
        ),
        Index("ix_resume_versions_status", "status"),
        Index("uq_resume_versions_upload_idempotency_key", "upload_idempotency_key", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    resume_id: Mapped[str] = mapped_column(ForeignKey("resumes.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer)
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(512), unique=True)
    mime_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column(Integer)
    source_sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    upload_idempotency_key: Mapped[str | None] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class ResumeExtraction(Base):
    __tablename__ = "resume_extractions"
    __table_args__ = (
        UniqueConstraint("resume_version_id", "schema_version", "prompt_version", "model_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    resume_version_id: Mapped[str] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE")
    )
    schema_version: Mapped[str] = mapped_column(String(32))
    prompt_version: Mapped[str] = mapped_column(String(32))
    provider: Mapped[str] = mapped_column(String(80))
    model_id: Mapped[str] = mapped_column(String(160))
    extraction_json: Mapped[dict] = mapped_column(JSON)
    review_status: Mapped[str] = mapped_column(String(24), default="pending")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class ResumeConsent(Base):
    __tablename__ = "resume_consents"
    __table_args__ = (
        Index("ix_resume_consents_candidate_scope", "candidate_id", "scope", "revoked_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    resume_version_id: Mapped[str] = mapped_column(
        ForeignKey("resume_versions.id", ondelete="CASCADE")
    )
    scope: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime | None] = mapped_column(default=utc_now)
    revoked_at: Mapped[datetime | None]


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (Index("ix_jobs_organization_status", "organization_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(ForeignKey("organizations.id", ondelete="CASCADE"))
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    title: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class JobVersion(Base):
    __tablename__ = "job_versions"
    __table_args__ = (UniqueConstraint("job_id", "version_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column(Integer)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(24), default="draft")
    analysis_json: Mapped[dict | None] = mapped_column(JSON)
    prompt_version: Mapped[str | None] = mapped_column(String(32))
    provider: Mapped[str | None] = mapped_column(String(80))
    model_id: Mapped[str | None] = mapped_column(String(160))
    approved_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class JobRequirement(Base):
    __tablename__ = "job_requirements"
    __table_args__ = (UniqueConstraint("job_version_id", "requirement_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_version_id: Mapped[str] = mapped_column(ForeignKey("job_versions.id", ondelete="CASCADE"))
    requirement_key: Mapped[str] = mapped_column(String(120))
    requirement_type: Mapped[str] = mapped_column(String(24))
    description: Mapped[str] = mapped_column(Text)
    evidence: Mapped[list] = mapped_column(JSON, default=list)


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        UniqueConstraint("job_id", "candidate_id"),
        Index("ix_applications_job_status", "job_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    resume_version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"))
    status: Mapped[str] = mapped_column(String(24), default="submitted")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    __table_args__ = (
        UniqueConstraint("idempotency_key"),
        CheckConstraint(
            "status IN ('queued', 'processing', 'retry_wait', 'succeeded', "
            "'dead_letter', 'blocked')"
        ),
        Index("ix_processing_jobs_ready", "status", "available_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_type: Mapped[str] = mapped_column(String(24))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    job_type: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(20), default="queued")
    attempt_count: Mapped[int] = mapped_column(Integer, default=0)
    available_at: Mapped[datetime] = mapped_column(default=utc_now)
    locked_until: Mapped[datetime | None]
    worker_id: Mapped[str | None] = mapped_column(String(100))
    idempotency_key: Mapped[str] = mapped_column(String(128))
    last_error_code: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(default=utc_now, onupdate=utc_now)


class EmbeddingRecord(Base):
    __tablename__ = "embedding_records"
    __table_args__ = (UniqueConstraint("entity_type", "entity_id", "model_id", "content_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    entity_type: Mapped[str] = mapped_column(String(24))
    entity_id: Mapped[str] = mapped_column(String(36), index=True)
    model_id: Mapped[str] = mapped_column(String(160))
    dimensions: Mapped[int] = mapped_column(Integer)
    vector_json: Mapped[list] = mapped_column(JSON)
    content_hash: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class MatchRun(Base):
    __tablename__ = "match_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_version_id: Mapped[str] = mapped_column(ForeignKey("job_versions.id", ondelete="CASCADE"))
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24), default="queued")
    top_k: Mapped[int] = mapped_column(Integer, default=10)
    config_version: Mapped[str] = mapped_column(String(32), default="retrieval-v1")
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(default=None)
    error_message: Mapped[str | None] = mapped_column(String(500), default=None)


class MatchResult(Base):
    __tablename__ = "match_results"
    __table_args__ = (
        UniqueConstraint("match_run_id", "candidate_id"),
        Index("ix_match_results_rank", "match_run_id", "rank"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    match_run_id: Mapped[str] = mapped_column(ForeignKey("match_runs.id", ondelete="CASCADE"))
    candidate_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    resume_version_id: Mapped[str] = mapped_column(ForeignKey("resume_versions.id"))
    rank: Mapped[int] = mapped_column(Integer)
    retrieval_method: Mapped[str] = mapped_column(String(32))
    relevance_score: Mapped[float | None]
    dimensions_json: Mapped[dict] = mapped_column(JSON, default=dict)
    missing_requirements_json: Mapped[list] = mapped_column(JSON, default=list)
    evidence_json: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    __table_args__ = (Index("ix_audit_events_actor_created", "actor_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    actor_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(100))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(36))
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=utc_now)


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (Index("ix_notifications_owner_created", "user_id", "created_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    read_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(default=utc_now)
