# VERIFICATION_RUNBOOK: UMEC AI Planner

## Automated gates

Run from repository root:

1. `.venv/bin/ruff check services/api`
2. `.venv/bin/pytest services/api --cov=services/api/app --cov-report=term-missing`
3. `npm run worker:test`
4. `npm run web:test`
5. `npm run web:build`
6. `docker compose --env-file .env.example config -q`
7. `node tools/guards/check-file-lines.mjs`
8. `git diff --check`

Latest local result (2026-08-03): ruff passed; API 30/30, worker 3/3 and Web 8/8 tests passed; bounded conversation continuation, Google/Microsoft contact normalization, contact-first recipient resolution, ambiguous recipient guards, browser audio MIME parameters and Safari audio-only MP4 acceptance passed; Russian/English browser-locale resolution and localized OAuth errors passed; Next production build passed; Compose config passed; line guard and diff check passed. A real OpenAI continuation combined the original Teams request with a follow-up email and Moscow timezone into one complete meeting intent. Migration upgrade/downgrade/upgrade passed with the `Europe/Moscow` user default. Production smoke passed for invite registration, real OpenAI structured task/meeting intent, encrypted pending action visibility, cancellation and cleanup. A second production smoke created a due in-app reminder through the public HTTPS API and verified worker claim and delivery before removing the temporary account. VAPID public-key publication and private-key readability by the non-root worker were verified. Nginx security headers and auth rate limiting are active. API, Web, worker, database, Redis and backup containers report healthy. A checksum-verified production backup restored 11 tables into a disposable database and was removed after the drill.

## Migration drill

Against a disposable database, run `alembic upgrade head`, `alembic downgrade base`, then `alembic upgrade head`. Never downgrade production without a backup and reviewed migration.

## Backup drill

The `backup` service creates a custom-format `pg_dump`, validates its catalog, writes SHA-256 and retains 14 days. Restore only into an empty disposable database first using `infra/backup/restore.sh`; verify schema and row counts before scheduling a production maintenance window.

## Live provider acceptance

Use sandbox contacts only. For each family member:

1. Register with the family code and verify another member's tasks/integrations are absent.
2. Save an OpenAI key, transcribe a voice sample, and verify no key appears in API/log/audit output.
3. Authorize Google Calendar/Contacts, then Gmail read/compose/send incrementally.
4. Authorize Microsoft Calendar/Contacts/Teams, verify granted scopes.
5. Create a pending meeting action; cancel once and confirm a new one once.
6. Verify read-after-write result, meeting URL, participant invitation and audit record.
7. Change password and verify prior sessions are rejected.

Real OAuth acceptance remains blocked until the provider client IDs/secrets and interactive consent are supplied.
