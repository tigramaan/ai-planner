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

Latest local result (2026-08-03): ruff passed; API 36/36, worker 3/3 and Web 8/8 tests passed; bounded conversation continuation, calendar reschedule/cancel/participant matching, provider PATCH/DELETE verification, Google/Microsoft contact normalization, recipient ambiguity guards, browser audio variants and untrusted-host rejection passed; Russian/English browser-locale resolution and localized OAuth errors passed; Next production build passed; Compose config passed; line guard and diff check passed. Python dependency audit found no known vulnerabilities. npm audit reports three high advisories in the `postcss` and `sharp` versions bundled by the latest stable Next.js 16.2.12; no non-breaking stable Next update is currently available, and the application does not accept external CSS or image uploads. Real OpenAI intent checks recognized reschedule, cancellation and participant addition with Moscow-relative timestamps. A real continuation combined the original Teams request with a follow-up email and timezone into one meeting intent. Migration upgrade/downgrade/upgrade passed with the `Europe/Moscow` user default. Production smoke passed for invite registration, real OpenAI structured task/meeting intent, encrypted pending action visibility, cancellation and cleanup. A second production smoke created a due in-app reminder through the public HTTPS API and verified worker claim and delivery before removing the temporary account. VAPID public-key publication and private-key readability by the non-root worker were verified. Nginx security headers plus separate auth and AI request limits are active. API, Web, worker, database, Redis and backup containers report healthy. A checksum-verified production backup restored 11 tables into a disposable database and was removed after the drill.

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

Real OAuth acceptance requires provider consent for every production account.

## Security audit

Run the automated gates above, then verify the deployed boundary:

1. Anonymous requests to `/api/v1/me`, chat, planner and integration APIs return `401`.
2. Cross-origin preflight from an unlisted origin is rejected and untrusted `Host` values return `400`.
3. TLS is valid; HSTS, CSP, `nosniff`, referrer and permissions policies are present.
4. Login/setup/register and AI/voice routes have separate Nginx request limits.
5. `.env`, private keys and backups are ignored by Git and inaccessible to other host users.
6. API, Web and worker containers run as non-root; Postgres and Redis have no published ports.
7. OAuth state is hashed, expires after ten minutes, is provider-bound and single-use; provider tokens and pending actions are AES-GCM encrypted with context binding.
8. Calendar/mail writes require an immutable pending-action confirmation and provider read-after-write verification.
9. Rotate any provider credential disclosed outside the production secret store, then revoke the superseded value.
