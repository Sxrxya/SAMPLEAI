from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserCreate(StrictModel):
    email: EmailStr
    display_name: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=12, max_length=256)


class RecruiterCreate(UserCreate):
    organization_name: str = Field(min_length=2, max_length=200)


class LoginRequest(StrictModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class CandidateProfileUpdate(StrictModel):
    headline: str | None = Field(default=None, max_length=240)
    location: str | None = Field(default=None, max_length=160)
    preferences: dict = Field(default_factory=dict)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    display_name: str
    role: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: datetime
    user: UserResponse


class ResumeUploadResponse(BaseModel):
    resume_id: str
    resume_version_id: str
    processing_job_id: str | None
    status: str


class ProcessingStatusResponse(BaseModel):
    id: str
    status: str
    attempt_count: int
    last_error_code: str | None
    created_at: datetime


class JobCreateResponse(BaseModel):
    id: str
    version_id: str
    status: str
    analysis_job_id: str


class MatchResultResponse(BaseModel):
    rank: int
    candidate_id: str
    resume_version_id: str
    retrieval_method: str
    relevance_score: float | None = None
    dimensions: dict
    missing_requirements: list
    evidence: list


class Evidence(BaseModel):
    source: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=1000)
    page: int | None = Field(default=None, ge=1)


class SkillFact(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    evidence: list[Evidence] = Field(default_factory=list)


class WorkHistoryItem(BaseModel):
    employer: str | None = Field(default=None, max_length=200)
    title: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    description: str | None = Field(default=None, max_length=4000)
    evidence: list[Evidence] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str | None = Field(default=None, max_length=200)
    qualification: str | None = Field(default=None, max_length=200)
    field: str | None = Field(default=None, max_length=200)
    start_date: str | None = Field(default=None, max_length=32)
    end_date: str | None = Field(default=None, max_length=32)
    evidence: list[Evidence] = Field(default_factory=list)


class ProjectItem(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=3000)
    skills: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class ResumeExtractionPayload(StrictModel):
    schema_version: Literal["resume.v1"]
    headline: str | None = Field(default=None, max_length=240)
    location: str | None = Field(default=None, max_length=160)
    summary: str | None = Field(default=None, max_length=4000)
    skills: list[SkillFact] = Field(default_factory=list)
    work_history: list[WorkHistoryItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    languages: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)


class ResumeReviewRequest(StrictModel):
    extraction: ResumeExtractionPayload
    confirmed: bool


class ConsentRequest(StrictModel):
    consent: bool


class JobCreate(StrictModel):
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=20, max_length=30000)
    location: str | None = Field(default=None, max_length=160)


class JobRequirementFact(BaseModel):
    key: str = Field(min_length=1, max_length=120)
    requirement_type: Literal["required", "preferred"]
    description: str = Field(min_length=1, max_length=1000)
    evidence: list[Evidence] = Field(default_factory=list)


class JobExtractionPayload(StrictModel):
    schema_version: Literal["job.v1"]
    role_title: str
    location: str | None = None
    required_skills: list[JobRequirementFact] = Field(default_factory=list)
    preferred_skills: list[JobRequirementFact] = Field(default_factory=list)
    experience_requirements: list[JobRequirementFact] = Field(default_factory=list)
    education_requirements: list[JobRequirementFact] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    unknown_fields: list[str] = Field(default_factory=list)


class JobReviewRequest(StrictModel):
    extraction: JobExtractionPayload


class MatchRunRequest(StrictModel):
    top_k: int = Field(default=10, ge=1, le=10)


class ApplicationCreate(StrictModel):
    resume_version_id: str
    consent_to_share: Literal[True]


class ApplicationStatusUpdate(StrictModel):
    status: Literal["reviewing", "shortlisted", "interview", "rejected", "hired"]
    reason: str | None = Field(default=None, max_length=1000)


class VerificationDecision(StrictModel):
    decision: Literal["verified", "rejected"]
    reason: str | None = Field(default=None, max_length=1000)


class PaginatedResponse(BaseModel):
    items: list[dict]
    page: int
    page_size: int
    total: int
    pages: int
