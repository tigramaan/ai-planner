# System Spec: UMEC AI Planner

## Purpose

Self-hosted family command center for Russian and English text/voice commands. Each family member has an independent account, planner data and provider integrations. The system coordinates calendars, contacts, mail, tasks, reminders, timers and meeting links through explicit connectors and confirmation policies.

## Family access

- REQ-001: `tigramaan@gmail.com` is the bootstrap family administrator.
- REQ-002: Family members register only with a server-side invitation code and use local email/password authentication independently of Google and Microsoft.
- REQ-003: Every user can change their password after confirming the current password.
- REQ-004: Sessions use HttpOnly, Secure-in-production, SameSite=Strict cookies and can be revoked.
- REQ-005: Every integration, secret, task, message, pending action and audit row is owned by one user and inaccessible to other users.

## Architecture

- REQ-010: The system is implemented as independently deployable services under `services/*`.
- REQ-011: Services communicate only through documented HTTP/event contracts.
- REQ-012: Every service exposes a health procedure, config schema, tests and deployment notes.
- REQ-013: No source file exceeds 500 lines.
- REQ-014: Production is deployable at `https://planner.umec.space`.

## Product

- REQ-020: A responsive Web/PWA provides chat, voice capture, Today, tasks, timers, integration settings and audit.
- REQ-021: OpenAI performs transcription and structured intent extraction; secrets and OAuth tokens are never sent to the model.
- REQ-022: Google OAuth supports incremental Calendar, Contacts and Gmail scopes.
- REQ-023: Microsoft OAuth supports Outlook Calendar, Teams meetings, directory and mail.
- REQ-024: External writes require an immutable pending action and explicit confirmation by default.
- REQ-025: Local tasks and timers can be created without external confirmation.
- REQ-026: All external writes are idempotent and verified by reading the created resource.
- REQ-027: The Web/PWA and assistant responses support Russian and English. Locale is derived only from browser language preferences; unsupported preferences fall back to English and no manual override is stored.

## Security

- REQ-030: Passwords use Argon2id.
- REQ-031: Integration secrets use AES-256-GCM envelope encryption with a master key supplied only at runtime.
- REQ-032: API inputs, permissions, state, timeouts and upstream responses are validated before business logic.
- REQ-033: OAuth state is single-use, time-limited and bound to the authenticated user who started authorization.
- REQ-034: Logs and audit records redact credentials, tokens and message bodies where required.
- REQ-035: Untrusted mail/contact/calendar text cannot issue agent instructions.

## Constraints

- Store timestamps in UTC and retain the source IANA timezone.
- Do not commit secrets or production credentials.
- Automated tests must not contact real recipients or create real events.
