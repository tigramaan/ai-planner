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

Latest local result (2026-08-03): ruff passed; API planner suite includes authenticated Today/Week aggregation and anonymous-access rejection. The seven-day view uses the same guarded provider collector as Today, and Gmail 401/403 failures return localized reauthorization guidance rather than a raw upstream error. Calendar events apply the per-user reminder offset (five minutes by default), and an explicit Telemost/Yandex request overrides stale Teams context. Chat history is limited to the latest 50 messages in chronological order and the Web viewport follows new messages unless the user scrolls upward. Provider defaults, explicit-only video creation, Zoom OAuth/meeting verification, encrypted recipient aliases, encrypted Teams/Telemost fallback rooms, strict fallback URL allowlisting, partial calendar success when video creation fails, conversation continuation, calendar mutations, provider guards, browser audio and untrusted-host rejection passed. Russian/English browser-locale resolution, Next production build, Compose config, line guard and diff check passed. Production Python images require patched pip 26.1.2 and cryptography 48.0.1 or newer; development tooling requires patched pytest 9.0.3 or newer. npm audit retains three high advisories in dependencies bundled by Next.js 16.2.12; the application does not accept external CSS or image uploads, and npm currently offers only an invalid breaking downgrade rather than a safe fix. Migration upgrade/downgrade/upgrade passed through the reminder preference. Production smoke, VAPID access, Nginx security headers, auth/AI rate limits and all service health checks passed. A checksum-verified production backup restored 11 tables into a disposable database and was removed after the drill.

Cross-account security acceptance (2026-08-03): a second family member cannot list, update, delete, confirm or cancel the first member's tasks, timers, pending actions, reminders, chat, integrations, preferences, audit or agenda data. Foreign object identifiers return 404, encrypted fallback links remain private, a signed access token with a session belonging to another subject is rejected with 401, and public setup status does not reveal the administrator email.

Mobile chat acceptance (2026-08-03): the composer occupies the full chat width, expands from one line with typed, drafted or transcribed text up to 240 px, then scrolls internally. Microphone and send controls sit in a separate bottom action row and retain at least 50 px touch targets on mobile. Ctrl/Cmd+Enter sends while plain Enter creates a new line.

Flexible calendar lookup acceptance (2026-08-03): update/cancel/participant actions match partial titles, inflected participant names and attendee addresses. An inferred current time only ranks candidates and never filters out a strong name match. Multiple or weak matches are shown as numbered choices with local date/time, and a numeric follow-up reconstructs the unfinished action.

External action reporting acceptance (2026-08-03): meeting creation, event update/cancellation, participant addition and email sending always create a pending action with Confirm/Cancel controls. Confirmation by button or chat returns the same localized report with operation, title, local date/time, provider and participants. Calendar and video URLs are retained separately and rendered as clickable HTTPS links; partial video failures explicitly state that the calendar event was still saved.

Persistent session acceptance (2026-08-03): the access cookie lasts one day by default, and its expiry does not send an active user to login. The Web client performs one shared refresh for concurrent unauthorized requests, retries each original operation once, and protected pages remain reachable while the HttpOnly refresh cookie exists. Successful refresh extends the bounded server session without a multi-tab token-rotation race; logout, password change, revocation and refresh expiry still terminate access.

Adaptive logo acceptance (2026-08-03): navigation shows the supplied black UMEC mark on light surfaces and automatically renders the same transparent mark in white when the browser requests a dark color scheme. Switching the system theme updates the mark without a reload; PWA application icons retain their branded artwork.

Gmail OAuth callback acceptance (2026-08-03): Google denial, omitted Gmail permissions and a failed Gmail profile capability check redirect back to Settings with localized recovery instructions. The integration is persisted as connected only after the token's granted scopes cover the request and the Gmail API accepts the access token; a rejected callback never leaves a false connected record.

OAuth session-return acceptance (2026-08-03): access and refresh cookies are HttpOnly, Secure in production and SameSite=Lax. OAuth start reissues an existing session with the compatible attribute before leaving the site, so pre-fix browser sessions are repaired without another login. A top-level GET redirect from Google/Microsoft/Zoom retains the application session and reaches Settings rather than Login; cross-site POST requests still do not receive the cookies. OAuth state remains single-use and user-bound.

Family invitation and logout acceptance (2026-08-03): navigation provides an explicit logout action that revokes the current refresh session before returning to login. Every authenticated member can create and copy unlimited high-entropy invitation URLs from Settings; raw tokens are never stored, each expires after seven days and registers exactly one isolated non-admin account. Invite replay returns forbidden.

Public project acceptance (2026-08-03): Gitleaks reports zero findings across all 30 existing commits and zero findings in the new README, Pages, skill, workflows and security policy. CI checks out full history and blocks future leaks. The responsive GitHub Pages landing was rendered at 1440 px and includes real desktop/mobile screenshots, installation steps, provider support and an open contributor call. The repository `deploy-aiplanner` skill passes the official skill validator and explicitly prevents secret disclosure while configuring OpenAI, Google, Microsoft, Zoom, Yandex 360 and web push.

Additional UI acceptance (2026-08-03): Today/Week show start/end, timer trigger, attendees, reminders, safe meeting links, provider edit links, task completion/deletion, timer restart/deletion and calendar change/cancel drafts. PWA installation supports the browser prompt plus iOS/Android fallback instructions, with UMEC-branded manifest and Apple icons. Tasks support description, Moscow due date, priority, search, status/date filters, completion/reopening, inline editing, collapsed completed work and confirmed deletion; mutation endpoints enforce per-user ownership. Chat/voice support detailed task creation, update, completion, reopening and deletion plus timer restart/deletion. Command examples cover these mutations and open as chat drafts. Explicit Telemost selection overrides stale video context for both new and updated events, and a configured permanent room is written into the calendar event.

## Migration drill

Against a disposable database, run `alembic upgrade head`, `alembic downgrade base`, then `alembic upgrade head`. Never downgrade production without a backup and reviewed migration.

## Backup drill

The `backup` service creates a custom-format `pg_dump`, validates its catalog, writes SHA-256 and retains 14 days. Restore only into an empty disposable database first using `infra/backup/restore.sh`; verify schema and row counts before scheduling a production maintenance window.

## Live provider acceptance

Use sandbox contacts only. For each family member:

1. Create multiple member invite links, register through one, verify it cannot be reused, and verify another member's tasks/integrations are absent.
2. Create a task with a due date and priority; edit, complete, reopen and delete it, then verify a second user cannot mutate it.
3. Save an OpenAI key, transcribe a voice sample, and verify no key appears in API/log/audit output.

OpenAI latency acceptance (2026-08-03): the default planner model is `gpt-5.6-luna`; intent extraction sends explicit `reasoning.effort=low` through the Responses API. Unit tests must assert the reasoning request contract, while existing structured-intent and conversation tests guard behavior.

Gmail natural-search acceptance (2026-08-03): authorize Gmail read access, then verify «непрочитанные письма за сегодня» maps to `is:unread` plus local-day bounds and «письма от <имя> с документами» maps to sender plus attachment filters. Confirm the real mailbox returns the same records as Gmail UI without exposing tokens or message bodies in logs.
4. Authorize Google Calendar/Contacts, then Gmail read/compose/send incrementally.
5. Authorize Microsoft Calendar/Contacts/Teams, verify granted scopes.
6. Create a pending meeting action; cancel once and confirm a new one once.
7. Verify read-after-write result, meeting URL, participant invitation and audit record.
8. Change password and verify prior sessions are rejected.

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
