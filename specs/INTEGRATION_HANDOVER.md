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

Booking requires the owner's Google Calendar connection regardless of the general calendar default. Select Google Meet, Yandex Telemost, Zoom or no video in the booking block. Telemost requires the encrypted permanent room URL in general Settings; Zoom requires its OAuth connection. Availability and the final pre-write guard both read Google Calendar conflicts.
# Web Push deployment note

The VAPID private key is mounted read-only into the non-root worker. Keep it at mode `0640` and set `VAPID_FILE_GID` to the key file's numeric host group before `docker compose up`. The worker validates readability before publishing its Redis heartbeat. After deployment, use the authenticated **Проверить уведомление** action rather than relying only on the browser permission toggle.
