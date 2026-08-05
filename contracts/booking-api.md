# Booking API Contract

Booking API is a server-to-server boundary exposed by the API service. It has no browser form and accepts only `Authorization: Bearer <integration-key>`. Keys are scoped to one owner, shown once, stored only as hashes, revocable and audited.

Production routes the exact `/booking/v1/*` machine prefix through the Web gateway to the API service without browser-session middleware. The Bearer key remains the sole authorization boundary; owner `/api/v1/booking/*` settings stay behind browser authentication. Redirects and login HTML are never part of the machine contract.

## Owner endpoints

- `GET /api/v1/booking/settings` returns policy and key metadata, never the key.
- `PUT /api/v1/booking/settings` validates and updates availability rules.
- `POST /api/v1/booking/keys` creates or rotates the key and returns plaintext once.
- `DELETE /api/v1/booking/keys/{id}` revokes the owned key.

## Site endpoints

- `GET /booking/v1/availability?from=...&timezone=...` returns exact JSON `{timezone,duration_minutes,slots:[{start,end}]}` with at most 24 ordered UTC-offset intervals inside the next 14 days.
- `POST /booking/v1/bookings` requires `Idempotency-Key` and accepts `lead_id`, `name`, `email`, `start`, optional company and safe note.
- `GET /booking/v1/bookings/{id}` returns only a booking created through the same API key owner.

Booking uses the owner's connected Google Calendar only. The owner selects a dedicated booking conference default in Settings: Google Meet, Yandex Telemost, Zoom or no video. Telemost uses the encrypted permanent room configured by the owner; Zoom requires its connected integration. The site cannot override duration, organizer, calendar, conference provider or availability policy.

Availability reads Google events for the complete bounded window and applies configured buffers. Booking repeats that Google conflict check immediately before creation, creates the Google event with attendee updates, reads it back and only then consumes one of three successful attempts for `lead_id`. Failed provider calls and conflicts do not consume an attempt. Reusing an idempotency key with a different payload is rejected.

Contact fields are encrypted at rest. API responses expose no provider token or encrypted payload. Cancellation and rescheduling are outside this contract.
