# Integration Service Contract

Base: `/api/v1/integrations`. Supports list, encrypted provider configuration, test, OAuth start/callback and disconnect. Secret writes return only provider, state and timestamps.

The integration list may report the server-managed OpenAI fallback as configured without exposing its value. A per-user encrypted OpenAI key overrides this fallback.

Google incremental scopes: `openid email`, Calendar read/write, Contacts read, Gmail read/compose/send. Microsoft delegated scopes: `openid profile email offline_access User.Read Calendars.ReadWrite Contacts.Read Mail.Read Mail.ReadWrite Mail.Send OnlineMeetings.ReadWrite`.

All calls have explicit timeouts. OAuth state is one-time. External writes require a confirmed pending action and read-after-write verification.

Meeting and mail recipients may be supplied as names. The agent resolves names against connected provider contacts first and mail senders second, preferring the requested event provider and then other connected providers. A unique address is used in the pending confirmation; zero or multiple matches require user clarification.

Calendar adapters support read-after-write event creation, rescheduling, participant replacement and verified cancellation for Google Calendar and Microsoft Graph. Provider event identifiers never come from the model; they are selected from the authenticated user's bounded calendar search.
