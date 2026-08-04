# Booking API Contract

Booking API is a server-to-server boundary exposed by the API service. It has no browser form and accepts only `Authorization: Bearer <integration-key>`. Keys are scoped to one owner, shown once, stored only as hashes, revocable and audited.

## Owner endpoints

- `GET /api/v1/booking/settings` returns policy and key metadata, never the key.
- `PUT /api/v1/booking/settings` validates and updates availability rules.
- `POST /api/v1/booking/keys` creates or rotates the key and returns plaintext once.
- `DELETE /api/v1/booking/keys/{id}` revokes the owned key.

## Site endpoints

- `GET /booking/v1/availability?from=...&timezone=...` returns bounded available UTC-offset intervals.
- `POST /booking/v1/bookings` requires `Idempotency-Key` and accepts `lead_id`, `name`, `email`, `start`, optional company and safe note.
- `GET /booking/v1/bookings/{id}` returns only a booking created through the same API key owner.

The site cannot override duration, organizer, calendar, conference provider or availability policy. Availability and booking validate timezone, bounds and provider state. Booking repeats the conflict check, creates the provider event with attendee updates, reads it back and only then consumes one of three successful attempts for `lead_id`. Failed provider calls and conflicts do not consume an attempt. Reusing an idempotency key with a different payload is rejected.

Contact fields are encrypted at rest. API responses expose no provider token or encrypted payload. Cancellation and rescheduling are outside this contract.
