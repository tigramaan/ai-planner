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

- REQ-020: A responsive Web/PWA provides chat, voice capture with visible live recording feedback, Today, a seven-day agenda, tasks, timers, integration settings and audit. Voice upload supports browser-produced WebM and MP4/M4A variants.
- REQ-021: OpenAI performs transcription and structured intent extraction; secrets and OAuth tokens are never sent to the model.
- REQ-022: Google OAuth supports incremental Calendar, Contacts and Gmail scopes.
- REQ-023: Microsoft OAuth supports Outlook Calendar, Teams meetings, directory and mail.
- REQ-024: External writes require an immutable pending action and explicit confirmation by default.
- REQ-025: Local tasks and timers can be created without external confirmation.
- REQ-026: All external writes are idempotent and verified by reading the created, updated or deleted resource state.
- REQ-027: The Web/PWA and assistant responses support Russian and English. Locale is derived only from browser language preferences; unsupported preferences fall back to English and no manual override is stored.
- REQ-028: Existing Google/Microsoft events can be rescheduled, cancelled or extended with participants only after unique matching and explicit confirmation.
- REQ-047: The seven-day agenda combines the current user's local tasks, reminders, active timers and available Google/Microsoft calendar events; unavailable providers degrade without blocking local data.
- REQ-048: Mail-provider authorization failures are converted into localized reconnect guidance and never expose raw upstream errors to the user.
- REQ-049: Today and Week expose start/end, timer trigger, participants, reminder offset, safe meeting link and provider edit link. Calendar events can open a prefilled chat correction.
- REQ-050: The PWA exposes installation from the main screen and navigation, provides iOS/Android instructions, and ships branded manifest and Apple icons.
- REQ-051: The task workspace supports creation with description, Moscow due date and priority; search and status/date filters; completion and reopening; inline editing; confirmed deletion; and strict per-user ownership on every mutation.

## Security

- REQ-030: Passwords use Argon2id.
- REQ-031: Integration secrets use AES-256-GCM envelope encryption with a master key supplied only at runtime.
- REQ-032: API inputs, permissions, state, timeouts and upstream responses are validated before business logic.
- REQ-033: OAuth state is single-use, time-limited and bound to the authenticated user who started authorization.
- REQ-034: Logs and audit records redact credentials, tokens and message bodies where required.
- REQ-035: Untrusted mail/contact/calendar text cannot issue agent instructions.
- REQ-036: Named recipients are resolved from connected contacts and mail senders; ambiguous or missing matches require clarification.
- REQ-037: The agent resolves concise follow-up answers against recent conversation context without reviving completed actions.
- REQ-038: Every pending external action presents a localized human-readable summary; corrections replace the draft and an explicit affirmative chat reply executes only the latest version.
- REQ-039: An explicitly referenced cancelled, unexecuted draft can be corrected into a new draft; Google Calendar meetings may use a Microsoft Teams conference link when both integrations are authorized.
- REQ-040: An explicitly requested name-to-email mapping is stored per user with authenticated encryption and reused for later recipient resolution; provider failures return actionable API errors without an internal-server-error leak.
- REQ-041: Each user selects default calendar, mail and video providers. Defaults apply only when a requested capability omits its provider; a video meeting is never inferred from an ordinary meeting, call reminder or offline event.
- REQ-042: Calendar creation is independently useful: if an explicitly requested video provider is unavailable, the confirmed calendar event is still created and the result reports a partial-success warning.
- REQ-043: Zoom uses user-managed OAuth and verified meeting creation. Yandex Calendar/Mail use the documented CalDAV/IMAP/SMTP business-service path; Telemost API is offered only for eligible Yandex 360 Business organization accounts.
- REQ-044: A user may store encrypted permanent Teams and Telemost room URLs. They are used only for an explicitly requested provider when its API is unavailable, are inserted into the calendar event, and produce a visible shared-room warning.
- REQ-045: Chat initially loads only the latest 50 messages in chronological order and stays pinned to the newest message unless the user deliberately scrolls upward.
- REQ-046: Calendar events use a per-user reminder offset, defaulting to five minutes; zero disables it. An explicitly named video provider in the current message overrides defaults and conversation history.

## Constraints

- Store timestamps in UTC and retain the source IANA timezone. The default user timezone is `Europe/Moscow`.
- Do not commit secrets or production credentials.
- Automated tests must not contact real recipients or create real events.
