# Integration Service Contract

Base: `/api/v1/integrations`. Supports list, encrypted provider configuration, test, OAuth start/callback and disconnect. Secret writes return only provider, state and timestamps.

The integration list may report the server-managed OpenAI fallback as configured without exposing its value. A per-user encrypted OpenAI key overrides this fallback.

Google incremental scopes: `openid email`, Calendar read/write, Contacts read, Gmail read/compose/send. Microsoft delegated scopes: `openid profile email offline_access User.Read Calendars.ReadWrite Contacts.Read Mail.Read Mail.ReadWrite Mail.Send OnlineMeetings.ReadWrite`.

All calls have explicit timeouts. OAuth state is one-time. External writes require a confirmed pending action and read-after-write verification.

Gmail sending requires a connected user-owned integration with `gmail.compose` or `gmail.send`. The API builds an RFC email from the confirmed recipients, subject and body, calls Gmail only after confirmation, then verifies the returned message identifier. Missing write scope fails before a pending send action is created.

Calendar and conference providers are independent for new meetings. A Google Calendar event may carry a standalone Microsoft Teams URL: the Teams meeting is created idempotently and verified first, then the Google event is created with invitations and the join URL; a failed calendar write triggers deletion of the standalone Teams meeting.

Meeting and mail recipients may be supplied as names. The agent resolves names against paginated connected provider contacts first and validated mail sender identities second, preferring the requested event provider and then other connected providers. Matching normalizes case, punctuation, name order and Cyrillic/Latin spelling. Message subjects and bodies never make their senders candidates; technical/automated addresses and weak partial matches are excluded. At most three strongly relevant addresses are returned. A unique address is used in the pending confirmation; zero or multiple matches require user clarification.

If the owner explicitly asks to remember an email supplied after a missing-recipient clarification, the API stores an encrypted, per-user alias. Saved aliases are checked before external contacts and mail. Provider validation failures are returned as guarded `409`/`502` responses and never as an unhandled `500`.

User preferences select default calendar, mail and video providers. Calendar/mail defaults apply when the user omits a provider. The video default applies only after the user explicitly requests an online/video meeting; otherwise `conference=none`. A video-provider failure does not roll back a successfully creatable calendar event and is returned in `result.warnings`.

Zoom is authorized with user-managed OAuth and creates meetings through `/v2/users/me/meetings` with read-after-write verification. Yandex 360 Calendar/Mail require the documented organization service application and CalDAV/IMAP/SMTP access; Telemost REST API must remain disabled for accounts that are not eligible Yandex 360 Business organization users.

Calendar adapters support read-after-write event creation, rescheduling, participant replacement and verified cancellation for Google Calendar and Microsoft Graph. Provider event identifiers never come from the model; they are selected from the authenticated user's bounded calendar search.
