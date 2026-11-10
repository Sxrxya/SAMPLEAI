# Frontend Testing Notes

## Automated checks

Run from `frontend/`:

```powershell
npm run build
npm run lint
```

The production build includes TypeScript project checks. Component, browser integration, and accessibility automation are not configured in this initial project yet.

## Manual acceptance checks

1. Open `/` at desktop and mobile widths; verify the three portal previews and sign-in entry points.
2. Preview each role. Confirm changing workspace updates navigation and section access; signing out returns to the public page.
3. Test the recruiter matching view: expand/collapse evidence, verify score disclaimer and resume/job references, and confirm missing skills/confidence/completeness are visible.
4. Try invalid auth and job forms; ensure Zod validation blocks submission. Verify successful demo actions are labeled local-only.
5. Select a resume file and confirm the status remains clearly marked as demo/queued rather than implying a backend processed it.
6. Search and paginate table views; verify no-results text appears for unmatched queries.
7. Check keyboard focus, dialog close controls, reduced-motion behavior, narrow mobile layout, and horizontal table scrolling.
8. Before live integration, verify all routes, payloads, session expiry, server authorization, candidate consent, and private resume access against the actual FastAPI OpenAPI schema and integration tests.