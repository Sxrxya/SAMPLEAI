# FastAPI Integration Contract

**Status: broader frontend integration requirements.** A subset is now implemented by the separate backend; see [backend/API_CONTRACT.md](../backend/API_CONTRACT.md) for actual route paths and payloads. Paths below that are not listed there remain proposed and are not implemented.

## Common conventions

- Base URL is configured with `VITE_API_BASE_URL`; proposed prefix: `/api/v1`.
- Authenticated requests use `Authorization: Bearer <access_token>` in the current client adapter. The placeholder adapter keeps the access token in memory only and has no refresh flow. Replace this behavior only after confirming the backend's cookie/token and refresh design.
- JSON uses `application/json`; uploads use `multipart/form-data` and must be size/type checked by the server.
- Paginated lists should accept `page`, `page_size`, `search`, and domain filters, and return `{ "items": [], "page": 1, "page_size": 20, "total": 0, "pages": 0 }`.
- Errors should return a stable shape such as `{ "detail": "Human-readable message", "code": "stable_error_code", "request_id": "..." }` without exposing internal traces.
- All private resume access must be authorized server-side. Do not return permanent public file URLs.

## Authentication and account lifecycle

| Proposed route | Request | Response / requirement |
| --- | --- | --- |
| `POST /auth/register` | `{ name, email, password, role }` | Created account; role must be allow-listed and privileged roles must not be self-assigned. |
| `POST /auth/login` | `{ email, password }` | `{ access_token, token_type, expires_at, user: { id, role, name } }`. |
| `POST /auth/logout` | Authenticated | Revoke session/token where supported. |
| `POST /auth/refresh` | Backend-defined secure refresh credential | Rotated token/session response only if required by the existing auth design. Not currently called by the frontend. |
| `GET /auth/session` | Authenticated | Current user and effective permissions, used to hydrate role-protected routes. |

## Candidate portal

| Proposed route | Purpose and contract |
| --- | --- |
| `GET, PATCH /candidate/profile` | Read/update candidate contact, experience, skills, preferences, and profile completion fields. Validate ownership on every request. |
| `POST /candidate/resumes` | Multipart `file`; return `{ id, version, status, created_at }`. Response must not expose a public storage URL. |
| `GET /candidate/resumes/status` | Return processing state per resume: `queued`, `processing`, `review_required`, `complete`, or `failed`, with timestamps and safe error details. |
| `GET, PUT /candidate/resumes/{resume_id}/extracted` | Retrieve/update parsed fields; PUT accepts only reviewable extracted data and records candidate confirmation. |
| `PATCH /candidate/resumes/{resume_id}/consent` | `{ consent: boolean }`; consent is explicit, timestamped, revocable, and checked by recruiter-facing reads. |
| `GET /candidate/jobs` | Paginated search with location, work mode, employment type, and skill filters. |
| `GET /candidate/jobs/{job_id}` | Public-to-candidate job detail, eligibility, and application state. |
| `POST /candidate/jobs/{job_id}/applications` | `{ resume_id, consent: true }`; server verifies the candidate owns the resume and has granted required sharing consent. |
| `GET /candidate/applications`, `GET /candidate/applications/{id}` | Return candidate-owned application status/history and allowed employer/job information. |
| `POST /candidate/applications/{id}/withdraw` | Candidate-owned withdrawal with auditable status transition. |

## Recruiter and employer portal

| Proposed route | Purpose and contract |
| --- | --- |
| `GET, PATCH /employer/company` | Read/update organization profile; writes require employer membership and verified/allowed state. |
| `GET, POST /employer/jobs`, `GET, PATCH /employer/jobs/{job_id}` | Paginated job management and job creation/editing. Include draft/active/paused/closed states and employer ownership checks. |
| `POST /employer/jobs/{job_id}/description/upload` | Multipart job-description document upload; return processing status, not fabricated requirements. |
| `GET, PUT /employer/jobs/{job_id}/description` | Review/update extracted job requirements before matching is requested. |
| `GET /recruiter/dashboard` | Recruiter-authorized summary counts and trends. |
| `GET /recruiter/jobs/{job_id}/applicants` | Paginated applicants visible to the authorized employer; include application status and consent-safe profile fields. |
| `GET /recruiter/candidates/{candidate_id}` | Candidate detail only when the recruiter has a permitted relationship and current consent. |
| `GET /recruiter/jobs/{job_id}/matches` | Paginated backend results. Each item must include `candidate_id`, `resume_id`, `resume_version`, `job_id`, `overall_score`, `dimensions`, `missing_skills`, `confidence`, `information_completeness`, and evidence references/text. Scores are not hiring probabilities. |
| `GET /recruiter/jobs/{job_id}/matches/{candidate_id}/evidence` | Authorized evidence supporting returned backend match dimensions. Do not recalculate scores in React. |
| `POST /recruiter/jobs/{job_id}/matches/compare` | `{ candidate_ids: string[] }`; return the same backend attributes for comparison, with access checks per candidate. |
| `PATCH /recruiter/applications/{application_id}/status` | `{ status }`; server validates state transitions and records actor/time/reason. AI score must not automatically reject candidates. |
| `POST /recruiter/interviews` | `{ application_id, starts_at, duration_minutes, interviewers, location_or_link }`; validate timezone and access. |
| `GET /recruiter/interviews` | Paginated authorized interview schedule. |
| `POST /recruiter/assessments`, `GET /recruiter/assessments` | Create/list assessments associated with a job/application, including status and due date. |

## Super admin portal

Every route below must require a distinct backend admin permission, audit privileged reads/writes, and avoid returning secrets.

| Proposed route | Purpose |
| --- | --- |
| `GET /admin/dashboard` | Platform-wide authorized summary. |
| `GET /admin/users?role=...` | Candidate, employer, and recruiter management with pagination/search. |
| `GET /admin/verifications`, `PATCH /admin/verifications/{id}` | Company verification queue and audited decision. |
| `GET /admin/jobs/moderation`, `PATCH /admin/jobs/{id}/moderation` | Job moderation queue and audited action/reason. |
| `GET /admin/processing/health`, `GET /admin/processing/jobs` | Resume/document processing health and job status; no resume contents unless separately authorized. |
| `GET, PATCH /admin/models/config` | Read/update allowed model deployment metadata/configuration; never expose credentials or trigger model changes without backend controls. |
| `GET, PATCH /admin/matching/config` | Read/update backend-owned matching configuration only; frontend must not calculate or override weights. |
| `GET, PATCH /admin/permissions` | Read/update permission assignments with step-up authorization and audit history. |
| `GET, PATCH /admin/data-retention` | Read/update retention policy metadata; deletion must be enforced by the backend. |
| `GET /admin/audit-events` | Filtered, paginated, read-only audit events. |
| `GET /admin/system/health` | Safe health status; no internal secrets, stack traces, or sensitive infrastructure details. |

## Shared services

| Proposed route | Purpose |
| --- | --- |
| `GET /notifications` | Paginated notifications scoped to the current account; supports `unread_only`. |
| `PATCH /notifications/{id}/read` | Mark only an owned notification as read. |
| `GET /health` | Minimal readiness check for deployment monitoring; public exposure is optional and backend-controlled. |

## Match response shape

This example documents fields only; numeric values must always be returned by the existing backend matching pipeline.

```json
{
  "candidate_id": "candidate-id",
  "resume_id": "resume-id",
  "resume_version": 3,
  "job_id": "job-id",
  "overall_score": 0,
  "dimensions": {
    "required_skills": 0,
    "semantic_relevance": 0,
    "experience_relevance": 0,
    "project_relevance": 0,
    "education_relevance": 0,
    "preferred_skills": 0
  },
  "missing_skills": [],
  "evidence": [{ "dimension": "required_skills", "source": "resume-section-reference", "text": "..." }],
  "confidence": "medium",
  "information_completeness": 0
}
```

The frontend must display this response faithfully, show its job/resume references, expose evidence, and never describe `overall_score` as a probability or automate rejection from it.