# Integration Service Contract

Base: `/api/v1/integrations`. Supports list, encrypted provider configuration, test, OAuth start/callback and disconnect. Secret writes return only provider, state and timestamps.

The integration list may report the server-managed OpenAI fallback as configured without exposing its value. A per-user encrypted OpenAI key overrides this fallback.

Google incremental scopes: `openid email`, Calendar read/write, Contacts read, Gmail read/compose/send. Microsoft delegated scopes: `openid profile email offline_access User.Read Calendars.ReadWrite Contacts.Read Mail.Read Mail.ReadWrite Mail.Send OnlineMeetings.ReadWrite`.

All calls have explicit timeouts. OAuth state is one-time. External writes require a confirmed pending action and read-after-write verification.

Calendar and conference providers are independent for new meetings. A Google Calendar event may carry a standalone Microsoft Teams URL: the Teams meeting is created idempotently and verified first, then the Google event is created with invitations and the join URL; a failed calendar write triggers deletion of the standalone Teams meeting.

Meeting and mail recipients may be supplied as names. The agent resolves names against connected provider contacts first and mail senders second, preferring the requested event provider and then other connected providers. A unique address is used in the pending confirmation; zero or multiple matches require user clarification.

If the owner explicitly asks to remember an email supplied after a missing-recipient clarification, the API stores an encrypted, per-user alias. Saved aliases are checked before external contacts and mail. Provider validation failures are returned as guarded `409`/`502` responses and never as an unhandled `500`.

Calendar adapters support read-after-write event creation, rescheduling, participant replacement and verified cancellation for Google Calendar and Microsoft Graph. Provider event identifiers never come from the model; they are selected from the authenticated user's bounded calendar search.
