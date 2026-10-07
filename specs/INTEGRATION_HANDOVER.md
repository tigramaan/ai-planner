# INTEGRATION_HANDOVER: UMEC AI Planner

## Required owner actions

1. Set a strong bootstrap administrator password, family registration code and 32-byte master key in the production secret store.
2. In Google Cloud create a Web OAuth client with callback `https://planner.umec.space/api/v1/integrations/google/oauth/callback`; enable Calendar, People and Gmail APIs.
3. In Microsoft Entra create a Web app with callback `https://planner.umec.space/api/v1/integrations/microsoft/oauth/callback`; allow delegated Graph permissions listed in `contracts/integration-service.md`.
4. Sign in as `tigramaan@gmail.com`, invite family members with the registration code, and let each user connect their own Google/Microsoft accounts from Settings.
5. Run the live acceptance checklist with sandbox contacts only.

OpenAI API billing is managed separately from ChatGPT subscriptions. Production uses the existing server API key; configure project usage limits and alerts in the OpenAI Platform billing settings because ChatGPT Plus/Pro credits cannot be applied to API traffic.

Provider client secrets and OAuth tokens are runtime data. They must never be committed.

## Website booking handover

The owner enables the booking API and creates a website key in Settings. Copy the key immediately into the website backend secret store; AI Planner never shows it again. Browser code must never receive this key. The backend uses `GET /booking/v1/availability` and `POST /booking/v1/bookings` with a unique `Idempotency-Key`. Stable `lead_id` values enforce the limit of three successful bookings per lead.

The production Web gateway must proxy the exact `/booking/v1/:path*` prefix to the internal API and exempt only that prefix from browser-session redirects. Do not expose or exempt `/api/v1/booking/*`: those owner settings remain browser-authenticated. Verify an anonymous machine request receives an API JSON status rather than `/login` before enabling a consuming site.

Booking requires the owner's Google Calendar connection regardless of the general calendar default. Select Google Meet, Yandex Telemost, Zoom or no video in the booking block. Telemost requires the encrypted permanent room URL in general Settings; Zoom requires its OAuth connection. Availability and the final pre-write guard both read Google Calendar conflicts.
# Web Push deployment note

The VAPID private key is mounted read-only as a source secret. The root-only worker entrypoint copies it to an ephemeral `0400` file owned by the non-root `planner` user before dropping privileges. Host group IDs are not part of the runtime contract. Keep the host source key private (`0640` or stricter). The worker validates readability before publishing its Redis heartbeat. After deployment, use the authenticated **Проверить уведомление** action rather than relying only on the browser permission toggle.

Install `infra/systemd/aiplanner.service` as `/etc/systemd/system/aiplanner.service`, enable it and keep Docker enabled. Its watchdog reconciles the Compose project after boot and recreates missing, stopped or unhealthy services. The API entrypoint retries its PostgreSQL migration until the database is ready, so Docker's parallel restart order cannot leave the API permanently stopped.

## Locale and icon upgrade (AP-018)

Web keeps the existing first-supported-browser-language policy, public asset paths
and API locale contract. Initial HTML is now request-localized and hydrates with
the same locale. English placed before Russian in browser preferences still
selects English. The request header never becomes a persisted user setting.

Application icons use the calendar AI mark; the UMEC navigation logo is retained.
Rebuild/deploy only Web; no schema migration is required. Previously installed
PWAs can refresh their home-screen icon on the operating system's own schedule;
new installations read the versioned manifest assets.

Regenerate PNG assets after changing services/web/public/icon.svg with npm ci followed by node tools/branding/generate-icons.mjs; sharp 0.34.5 is a pinned development dependency.

## GPT-6 upgrade (AP-019)

Use the existing OpenAI key. Set OPENAI_PLANNER_MODEL and OPENAI_JUNIOR_MODEL to
gpt-6.1-sol, OPENAI_SENIOR_MODEL to gpt-6.1-sol; keep planner/junior low and senior
medium. New-secret/Web defaults match Sol. Explicit per-user saved model settings
are preserved, including mail-analysis overrides. Tiered chat ignores that model
override and always uses the two server-configured tiers. No database migration
or API-client migration is required.

Rebuild API and Web, recreate those services and verify effective model fields
without reading secrets. Keep prior image tags and record the previous model
settings for rollback. Existing API timeouts/retries, six-round senior loop,
pending-action confirmation and transcription are unchanged.
