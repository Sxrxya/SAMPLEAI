# Tandem Recruitment Platform Frontend

A React + TypeScript frontend prototype for candidate, recruiter/employer, and super-admin workflows. It runs in an explicitly labeled demo mode; sample records are isolated in `src/mocks/` and are not production data. The separate FastAPI backend is documented in [backend/README.md](../backend/README.md).

## Requirements

- Node.js 20.19+ or 22.12+
- npm
- Python 3.10+ only if you want to use the repository's `.venv`; it is not required by this frontend

## Run locally

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Vite prints the local URL after startup. Set `VITE_API_BASE_URL=http://localhost:8000/api/v1` for the local backend. `VITE_USE_MOCKS=false` currently hides sample records and shows a not-connected state; the React pages/services have not yet been wired to the implemented backend workflows.

## Available commands

```powershell
npm run dev       # Start Vite
npm run build     # Type-check and create production assets in dist/
npm run preview   # Serve the production build locally
npm run lint      # Run Oxlint
```

## Application areas

- Candidate: profile, resume processing/review, consent, job discovery, applications, notifications, and settings.
- Recruiter/employer: company workspace, job management, applicants, backend match evidence, interviews, and analytics.
- Super admin: users, company verification, moderation, processing, model/matching settings, permissions, retention, audit, and health.

Role routes are guarded in the frontend for navigation and UX. The local demo role selector is not authentication; production authorization, consent enforcement, private document access, and all sensitive operations must be enforced by FastAPI.

## API integration status

The broad requirements are listed in [API_CONTRACT.md](API_CONTRACT.md). The routes that currently exist and their payloads are documented in [backend/API_CONTRACT.md](../backend/API_CONTRACT.md). Some proposed routes and payload names still differ, so reconcile service adapters before enabling live workflows. The React app does not calculate matching scores; live match values and evidence must come from the backend.

## Production deployment

1. Reconcile frontend services and forms with the implemented routes in `../backend/API_CONTRACT.md`.
2. Provide `VITE_API_BASE_URL` at build time and implement authenticated request/session handling before disabling mocks.
3. Run `npm ci` and `npm run build`; publish `dist/` to a static host or web server.
4. Configure SPA history fallback to `index.html`, HTTPS, allowed backend origins, and restrictive security headers.
5. Keep secrets exclusively on the backend. Do not expose private resume URLs or admin configuration credentials to browser code.
6. Validate authentication expiry, candidate consent, upload limits, recruiter access boundaries, and admin permissions with the real API before production release.

## Current limitations

Authentication screens, file selection, record actions, and dashboard data are UI previews. They do not yet persist through the FastAPI services. Automated frontend component/integration tests are not configured; see [TESTING.md](TESTING.md).
