# Implemented API Contract

Base prefix: `/api/v1`. These routes are implemented in this backend. Authentication uses a short-lived JWT bearer token backed by a revocable `auth_sessions` row. Public registration permits candidate and recruiter roles only; create the first admin with the private bootstrap CLI.

Errors use `{ "detail": "...", "code": "http_...", "request_id": "..." }` for HTTP errors. Validation errors currently use FastAPI's standard 422 envelope. Responses do not expose storage paths or provider credentials.

## Authentication

| Route | Request / response |
| --- | --- |
| `POST /auth/register` | Candidate `{ email, display_name, password }`; returns `{ access_token, token_type, expires_at, user }`. Password minimum is 12 characters. |
| `POST /auth/register/recruiter` | `{ email, display_name, password, organization_name }`; creates a pending-verification company and owner membership. |
| `POST /auth/login` | `{ email, password }`; returns access token and user. |
| `GET /auth/session` | Returns current authenticated user. |
| `POST /auth/logout` | Revokes the current session; returns 204. |
| `GET /health` | Minimal health response. |

Admin registration is intentionally not public. The first admin is created by `python -m app.bootstrap_admin` after migrations.

## Candidate

| Route | Request / response |
| --- | --- |
| `GET, PATCH /candidate/profile` | Candidate-owned profile. PATCH accepts `headline`, `location`, `preferences`. |
| `POST /candidate/resumes` | Multipart `file` plus `consent_to_ai_processing` boolean form field; optional `Idempotency-Key`. Returns 202 `{ resume_id, resume_version_id, processing_job_id, status }`. Without AI-processing consent the file is stored as `needs_consent` and not queued. |
| `POST /candidate/resumes/{version_id}/processing-consent` | `{ consent: true/false }`; granting queues processing. |
| `GET /candidate/resumes/{version_id}/status` | Status and processing attempt/error metadata. |
| `GET /candidate/resumes/{version_id}/extracted` | Candidate-owned validated `resume.v1` extraction. |
| `PUT /candidate/resumes/{version_id}/extracted` | `{ extraction: <resume.v1>, confirmed: true }`; confirms candidate review. |
| `PATCH /candidate/resumes/{version_id}/consent` | `{ consent: true/false }`; grants/revokes recruiter-search consent. |
| `GET /candidate/resumes/{version_id}/file` | Candidate-owned private file response with `private, no-store`. |
| `GET /candidate/jobs?page=1&page_size=20&search=...` | Paginated active jobs. |
| `GET /candidate/jobs/{job_id}` | Active job details and approved requirements. |
| `POST /candidate/jobs/{job_id}/applications` | `{ resume_version_id, consent_to_share: true }`; application-scoped organization consent is recorded. |
| `GET /candidate/applications?page=1&page_size=20&status=...` | Candidate-owned paginated applications. |
| `GET /candidate/applications/{id}` | Candidate-owned application detail. |
| `POST /candidate/applications/{id}/withdraw` | Candidate-owned withdrawal with audit event. |

## Employer and recruiter

| Route | Request / response |
| --- | --- |
| `POST /employer/jobs` | `{ title, description, location? }`, optional idempotency key. Returns 202 with job/version/analysis-job IDs. |
| `GET /employer/jobs?page=1&page_size=20` | Jobs belonging to recruiter organizations. |
| `GET /employer/jobs/{job_id}/description` | Organization-authorized JD version and analysis. |
| `PUT /employer/jobs/{job_id}/description` | `{ extraction: <job.v1> }`; recruiter-reviewed requirements are persisted. |
| `POST /employer/jobs/{job_id}/approve` | Publishes only reviewed JD versions for verified organizations. |
| `POST /recruiter/jobs/{job_id}/match-runs` | `{ top_k: 1..10 }`; requires an approved JD, returns 202 `{ match_run_id, processing_job_id }`. |
| `GET /recruiter/match-runs/{run_id}` | Organization-authorized status, job version, rank-ordered results and evidence. |
| `GET /recruiter/jobs/{job_id}/applicants` | Lists applications for an organization-owned job only. |
| `PATCH /recruiter/applications/{id}/status` | `{ status, reason? }`; human-entered state change recorded in audit log. |
| `GET /recruiter/applications/{id}/resume` | Private file only while application consent for the recruiter organization is active. |

Recruiter registration creates organizations as `pending_verification`. Admins use the routes below before a company can publish jobs.

## Administration

| Route | Request / response |
| --- | --- |
| `GET /admin/verifications?page=1&page_size=20` | Pending company verification queue. |
| `PATCH /admin/verifications/{organization_id}` | `{ decision: "verified"|"rejected", reason? }`; decision is audited. |
| `GET /admin/processing/jobs?page=1&page_size=20&status=...` | Queue status and safe error codes, not document contents. |
| `POST /admin/processing/jobs/{job_id}/retry` | Requeues a blocked/dead-letter job and audits the operator. |

## Processing and matching behavior

Resume statuses: `needs_consent`, `queued`, `processing`, `needs_review`, `complete`, `failed`. Queue statuses: `queued`, `processing`, `retry_wait`, `succeeded`, `blocked`, `dead_letter`. Blocked means provider configuration is unavailable and does not consume repeated API retries.

Job versions move through `draft`, `processing`, `needs_review`, `reviewed`, `approved`, or `failed`. Recruiters must review extracted requirements before approval.

Matching filters to complete, candidate-reviewed extractions with active `recruiter_search` consent. It retrieves a bounded FTS5 pool and adds cosine retrieval over stored vectors when a matching embedding model is configured. Results expose the semantic similarity signal and matched/missing required skills; they are not hiring probabilities. This MVP has no separate reranker or tuned scoring weights.

## Frontend integration note

The existing frontend demo services currently use some earlier proposed shapes. Before setting `VITE_USE_MOCKS=false`, align registration (`display_name`; recruiter-specific route), upload (`consent_to_ai_processing` form field), status route (requires resume version ID), application request (`resume_version_id`, `consent_to_share`), and matching (create a run, poll/read `/recruiter/match-runs/{id}`). The frontend was not modified as part of this backend implementation.