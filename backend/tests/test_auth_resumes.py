from io import BytesIO

from docx import Document


def register_candidate(client, email="candidate@example.com"):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "display_name": "Test Candidate",
            "password": "long-test-password-123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def make_docx() -> bytes:
    document = Document()
    document.add_paragraph("Senior software engineer with Python and FastAPI experience.")
    stream = BytesIO()
    document.save(stream)
    return stream.getvalue()


def test_authentication_register_login_and_logout(client):
    registration = register_candidate(client)
    token = registration["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/api/v1/auth/session", headers=headers).status_code == 200
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/session", headers=headers).status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@example.com", "password": "long-test-password-123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "candidate"


def test_resume_upload_is_private_idempotent_and_consent_gated(client):
    first = register_candidate(client)
    second = register_candidate(client, "another@example.com")
    token = first["access_token"]
    headers = {"Authorization": f"Bearer {token}", "Idempotency-Key": "upload-1"}
    file = (
        "resume.docx",
        make_docx(),
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    response = client.post(
        "/api/v1/candidate/resumes",
        headers=headers,
        data={"consent_to_ai_processing": "false"},
        files={"file": file},
    )
    assert response.status_code == 202
    payload = response.json()
    assert payload["status"] == "needs_consent"
    assert payload["processing_job_id"] is None

    version_id = payload["resume_version_id"]
    assert (
        client.get(f"/api/v1/candidate/resumes/{version_id}/file", headers=headers).status_code
        == 200
    )
    other_headers = {"Authorization": f"Bearer {second['access_token']}"}
    assert (
        client.get(
            f"/api/v1/candidate/resumes/{version_id}/status", headers=other_headers
        ).status_code
        == 404
    )

    consent = client.post(
        f"/api/v1/candidate/resumes/{version_id}/processing-consent",
        headers=headers,
        json={"consent": True},
    )
    assert consent.status_code == 200
    assert consent.json()["consent_to_ai_processing"] is True


def test_upload_requires_auth_and_rejects_unsupported_extensions(client):
    file = ("resume.exe", b"not a resume", "application/octet-stream")
    unauthenticated = client.post(
        "/api/v1/candidate/resumes",
        data={"consent_to_ai_processing": "true"},
        files={"file": file},
    )
    assert unauthenticated.status_code == 401

    account = register_candidate(client)
    response = client.post(
        "/api/v1/candidate/resumes",
        headers={"Authorization": f"Bearer {account['access_token']}"},
        data={"consent_to_ai_processing": "true"},
        files={"file": file},
    )
    assert response.status_code == 415


def test_duplicate_upload_key_returns_existing_job(client):
    account = register_candidate(client)
    headers = {
        "Authorization": f"Bearer {account['access_token']}",
        "Idempotency-Key": "same-upload",
    }
    data = {"consent_to_ai_processing": "true"}
    files = {"file": ("resume.docx", make_docx(), "application/octet-stream")}
    first = client.post("/api/v1/candidate/resumes", headers=headers, data=data, files=files)
    second = client.post("/api/v1/candidate/resumes", headers=headers, data=data, files=files)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()


def test_upload_without_processing_consent_is_still_idempotent(client):
    account = register_candidate(client)
    headers = {
        "Authorization": f"Bearer {account['access_token']}",
        "Idempotency-Key": "no-consent-upload",
    }
    data = {"consent_to_ai_processing": "false"}
    files = {"file": ("resume.docx", make_docx(), "application/octet-stream")}
    first = client.post("/api/v1/candidate/resumes", headers=headers, data=data, files=files)
    second = client.post("/api/v1/candidate/resumes", headers=headers, data=data, files=files)

    assert first.status_code == second.status_code == 202
    assert first.json() == second.json()
    assert first.json()["status"] == "needs_consent"
