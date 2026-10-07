# EXECUTION_PLAN: UMEC AI Planner

1. **Foundation**: decisions, threat model, service contracts, config, Compose and CI.
2. **Security slice**: family accounts, invite-only registration, password rotation, sessions, per-user encrypted secrets and audit.
3. **Agent slice**: chat, voice transcription, typed intent, policy and pending actions.
4. **Google slice**: OAuth, Calendar/People/Gmail adapters and verification.
5. **Microsoft slice**: OAuth, Graph Calendar/Teams/Mail adapters and verification.
6. **Planner slice**: tasks, reminders, timers and Today aggregation.
7. **PWA slice**: protected mobile-first UI, voice recording and integration management.
8. **Hardening**: unit/integration/E2E tests, secret checks, backup/restore and deployment runbook.
9. **Booking API slice**: owner policy and hashed integration keys, provider-backed availability, guarded/idempotent lead booking and Settings UI without a public form.
10. **Shared task slice**: same-server participants, collaborative checklist, activity history and owner-controlled access without assignee workflow.

The first production acceptance path is login -> OpenAI configuration -> Google authorization -> voice command -> contact resolution -> immutable confirmation -> verified calendar event -> audit/Today.

## AP-018 — Browser locale and calendar AI icon (2026-10-07)

1. Specify first-supported-language selection, bounded Accept-Language parsing,
   hydration consistency, languagechange and public icon assets.
2. Implement a shared locale provider initialized by the server; keep API locale
   derived from the same browser preferences and keep English fallback.
3. Draw a font-independent SVG calendar/AI mark and generate the three PNG sizes.
4. Run Web tests, type/build, source line guard and Russian/English browser checks.
5. Deploy only the Web service at planner.umec.space; verify readiness and icon
   asset delivery. Record the Git revision and verification in the runbook.

Observability: html.lang exposes the active locale; React/browser errors must be
absent on hydration and language changes; public asset HTTP status, MIME type and
PNG dimensions expose branding deployment failures. Language selection does not
log account data or create persistent preferences. The untrusted request header is
limited to 4096 characters/32 ranges and maps only to the ru/en enum.

Deployment prerequisite discovered during AP-018: the former service-only npm install ignored the workspace lock and drifted from installed/tested dependencies. Use an allowlisted root context and npm ci, pinning Next to security-patched 16.3.6 in the existing 16.3 minor line; rerun Web tests/build after dependency synchronization.
