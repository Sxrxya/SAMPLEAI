import asyncio
from io import BytesIO

from docx import Document
from sqlalchemy import select

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.security import create_access_token, hash_password
from app.models import OrganizationMembership, User
from app.schemas import (
    Evidence,
    JobExtractionPayload,
    JobRequirementFact,
    ResumeExtractionPayload,
    SkillFact,
)


class FakeHostedInference:
    async def extract_resume(self, _source_text):
        return (
            ResumeExtractionPayload(
                schema_version="resume.v1",
                headline="Backend engineer",
                skills=[
                    SkillFact(
                        name="FastAPI",
                        evidence=[
                            Evidence(source="work_history[0]", text="Built FastAPI services")
                        ],
                    )
                ],
            ),
            "test-chat-v1",
        )

    async def extract_job(self, _source_text):
        return (
            JobExtractionPayload(
                schema_version="job.v1",
                role_title="Backend Engineer",
                required_skills=[
                    JobRequirementFact(
                        key="fastapi",
                        requirement_type="required",
                        description="FastAPI experience",
                        evidence=[
                            Evidence(source="description", text="FastAPI experience required")
                        ],
                    )
                ],
            ),
            "test-chat-v1",
        )

    async def embed(self, _text):
        return [1.0, 0.0], "test-embedding-v1"


def _docx_bytes():
    document = Document()
    document.add_paragraph("Backend engineer with FastAPI experience.")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_candidate_to_recruiter_matching_flow(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "inference_enabled", True)
    monkeypatch.setattr(settings, "inference_chat_model", "test-chat-v1")
    monkeypatch.setattr(settings, "inference_embedding_model", "test-embedding-v1")
    monkeypatch.setattr("app.worker.HostedInferenceClient", FakeHostedInference)

    candidate_auth = client.post(
        "/api/v1/auth/register",
        json={
            "email": "candidate-flow@example.com",
            "display_name": "Candidate Flow",
            "password": "long-test-password-123",
        },
    ).json()
    candidate_headers = {"Authorization": f"Bearer {candidate_auth['access_token']}"}
    uploaded = client.post(
        "/api/v1/candidate/resumes",
        headers=candidate_headers,
        data={"consent_to_ai_processing": "true"},
        files={"file": ("resume.docx", _docx_bytes(), "application/octet-stream")},
    )
    assert uploaded.status_code == 202
    resume_version_id = uploaded.json()["resume_version_id"]

    from app.worker import process_job

    asyncio.run(process_job(uploaded.json()["processing_job_id"]))
    extraction_response = client.get(
        f"/api/v1/candidate/resumes/{resume_version_id}/extracted",
        headers=candidate_headers,
    )
    assert extraction_response.status_code == 200
    review = client.put(
        f"/api/v1/candidate/resumes/{resume_version_id}/extracted",
        headers=candidate_headers,
        json={"extraction": extraction_response.json(), "confirmed": True},
    )
    assert review.status_code == 200
    assert (
        client.patch(
            f"/api/v1/candidate/resumes/{resume_version_id}/consent",
            headers=candidate_headers,
            json={"consent": True},
        ).status_code
        == 200
    )

    recruiter_auth = client.post(
        "/api/v1/auth/register/recruiter",
        json={
            "email": "recruiter-flow@example.com",
            "display_name": "Recruiter Flow",
            "password": "long-test-password-456",
            "organization_name": "Example Hiring Co",
        },
    ).json()
    recruiter_headers = {"Authorization": f"Bearer {recruiter_auth['access_token']}"}

    with SessionLocal() as db:
        organization_id = db.scalar(
            select(OrganizationMembership.organization_id).where(
                OrganizationMembership.user_id == recruiter_auth["user"]["id"]
            )
        )
        admin = User(
            email="admin-flow@example.com",
            display_name="Test Admin",
            password_hash=hash_password("long-test-password-admin"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        admin_token, _ = create_access_token(db, admin)
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

    verified = client.patch(
        f"/api/v1/admin/verifications/{organization_id}",
        headers=admin_headers,
        json={"decision": "verified", "reason": "Test organization"},
    )
    assert verified.status_code == 200

    created_job = client.post(
        "/api/v1/employer/jobs",
        headers=recruiter_headers,
        json={
            "title": "Backend Engineer",
            "description": "Build and maintain FastAPI backend services for our product.",
            "location": "Remote",
        },
    )
    assert created_job.status_code == 202
    asyncio.run(process_job(created_job.json()["analysis_job_id"]))
    job_id = created_job.json()["id"]

    description = client.get(
        f"/api/v1/employer/jobs/{job_id}/description", headers=recruiter_headers
    ).json()
    reviewed = client.put(
        f"/api/v1/employer/jobs/{job_id}/description",
        headers=recruiter_headers,
        json={"extraction": description["analysis"]},
    )
    assert reviewed.status_code == 200
    assert (
        client.post(
            f"/api/v1/employer/jobs/{job_id}/approve", headers=recruiter_headers
        ).status_code
        == 200
    )

    match_run = client.post(
        f"/api/v1/recruiter/jobs/{job_id}/match-runs",
        headers=recruiter_headers,
        json={"top_k": 5},
    )
    assert match_run.status_code == 202
    asyncio.run(process_job(match_run.json()["processing_job_id"]))
    results = client.get(
        f"/api/v1/recruiter/match-runs/{match_run.json()['match_run_id']}",
        headers=recruiter_headers,
    )
    assert results.status_code == 200
    assert results.json()["results"][0]["candidate_id"] == candidate_auth["user"]["id"]
    assert results.json()["results"][0]["dimensions"]["required_skills"]["matched"] == ["fastapi"]

    application = client.post(
        f"/api/v1/candidate/jobs/{job_id}/applications",
        headers=candidate_headers,
        json={"resume_version_id": resume_version_id, "consent_to_share": True},
    )
    assert application.status_code == 201, application.text
    applicants = client.get(
        f"/api/v1/recruiter/jobs/{job_id}/applicants", headers=recruiter_headers
    )
    assert applicants.status_code == 200
    assert applicants.json()["items"][0]["candidate_id"] == candidate_auth["user"]["id"]
    resume_download = client.get(
        f"/api/v1/recruiter/applications/{application.json()['id']}/resume",
        headers=recruiter_headers,
    )
    assert resume_download.status_code == 200
