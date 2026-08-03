# System Spec: UMEC AI Planner

## Purpose

Self-hosted family command center for Russian and English text/voice commands. Each family member has an independent account, planner data and provider integrations. The system coordinates calendars, contacts, mail, tasks, reminders, timers and meeting links through explicit connectors and confirmation policies.

## Family access

- REQ-001: `tigramaan@gmail.com` is the bootstrap family administrator.
- REQ-002: Family members register only with a server-side invitation code and use local email/password authentication independently of Google and Microsoft.
- REQ-003: Every user can change their password after confirming the current password.
- REQ-004: Sessions use HttpOnly, Secure-in-production, SameSite=Lax cookies so OAuth top-level GET callbacks retain login while cross-site POSTs remain excluded; sessions can be revoked.
- REQ-005: Every integration, secret, task, message, pending action and audit row is owned by one user and inaccessible to other users.
- REQ-006: Every account has independent credentials, sessions, preferences, provider identities, OAuth tokens, fallback links, planner items, chat history and external calendar/mail views. Only application infrastructure and server-level API configuration are shared.

## Architecture

- REQ-010: The system is implemented as independently deployable services under `services/*`.
- REQ-011: Services communicate only through documented HTTP/event contracts.
- REQ-012: Every service exposes a health procedure, config schema, tests and deployment notes.
- REQ-013: No source file exceeds 500 lines.
- REQ-014: Production is deployable at `https://planner.umec.space`.

## Product

- REQ-020: A responsive Web/PWA provides chat, voice capture with visible live recording feedback, Today, a seven-day agenda, tasks, timers, integration settings and audit. Voice upload supports browser-produced WebM and MP4/M4A variants.
- REQ-021: OpenAI performs transcription and structured intent extraction; secrets and OAuth tokens are never sent to the model. The default planner route uses `gpt-5.6-luna` with explicit low reasoning effort for latency-sensitive structured extraction.
- REQ-022: Natural-language mail requests are translated into provider-native search filters, including unread state, local-day bounds, attachments and named senders; provider tokens remain outside the model.
- REQ-023: On an explicit summary request, the first matching Gmail message and up to five supported attachments are fetched with bounded sizes, locally converted to text and summarized by the configured model with storage disabled and prompt-injection isolation. Supported attachment extraction includes text, HTML, CSV, PDF, DOCX and XLSX.
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
- REQ-052: Chat and voice intents support detailed task creation, task update/completion/reopening/deletion and timer restart/deletion. Today/Week expose guarded task/timer actions and calendar change/cancel drafts. Explicit Telemost selection also replaces the video service while updating an existing event, using the encrypted permanent room when configured.
- REQ-053: Command examples are diverse, categorized and clickable into the chat draft. Navigation and install icons use the supplied UMEC brand logo.

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
- REQ-054: Object access returns not-found for foreign-owned identifiers, and an access token is accepted only when its session belongs to the same token subject.
- REQ-055: The chat composer uses the full available width, automatically grows with entered or transcribed text up to a bounded height, and places voice/send actions in a separate bottom row with mobile touch targets.
- REQ-056: Calendar mutations identify events flexibly by partial title, participant name/address and approximate wording. Current time is an optional ranking hint, never a required identifier. Ambiguous or weak matches return numbered local-time choices that can be selected in the next chat reply.
- REQ-057: Every external create/update/delete/send action requires an explicit Confirm/Cancel pending action. After execution, chat reports the exact completed operation, title, local date/time, provider, participants, calendar link, video link and any partial-success warning; safe HTTPS links are clickable.
- REQ-058: Access tokens have a one-day default lifetime. An active user session survives their expiry through a transparent, deduplicated refresh and one retry of the original Web request. The refresh session has a sliding bounded lifetime; logout, password change, revocation or refresh expiry still require a new login.
- REQ-059: The navigation brand logo remains legible in the browser's light and dark color schemes, using the original black mark on light surfaces and an automatic white rendering on dark surfaces.
- REQ-060: An OAuth callback marks Gmail connected only after checking the actually granted scopes and a live Gmail capability request. Declines, missing permissions and disabled Gmail API return the user to Settings with localized recovery guidance and never store a false connected state.
- REQ-061: Every signed-in user can explicitly sign out and revoke the current session. Every authenticated member can create unlimited family/friend invitation links; each link contains a high-entropy token stored only as a hash, expires after seven days, is single-use, and creates an otherwise fully isolated non-admin account.
- REQ-062: The public repository provides a Russian-first README, responsive GitHub Pages product/install site with real screenshots, private vulnerability reporting guidance, full-history secret scanning in CI, and a validated agent skill for secure self-hosted deployment and provider onboarding.
- REQ-063: Public documentation contains no personal mailbox/chat data, uses a purpose-built capability infographic, and is distributed under the MIT license. Successful interactive Web actions expose a localized, accessible, transient outcome notification.
- REQ-064: The agent can draft a ready-to-send Gmail message from a natural-language communication goal, resolve its recipients, preview the exact subject and body in a mandatory pending confirmation, and send only after explicit confirmation with Gmail compose/send scope and read-after-write verification.
- REQ-065: Starting or restarting a timer schedules exactly one linked Web Push delivery at its end time; renaming resynchronizes the notification, deletion removes it, and active timers are backfilled during migration. Timer delivery is not duplicated in Today/Week. If no browser subscription exists, chat gives actionable setup guidance and the worker uses bounded retries instead of falsely marking the push delivered.

## Constraints

- Store timestamps in UTC and retain the source IANA timezone. The default user timezone is `Europe/Moscow`.
- Do not commit secrets or production credentials.
- Automated tests must not contact real recipients or create real events.
