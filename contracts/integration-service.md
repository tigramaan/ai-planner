# Integration Service Contract

Base: `/api/v1/integrations`. Supports list, encrypted provider configuration, test, OAuth start/callback and disconnect. Secret writes return only provider, state and timestamps.

The integration list may report the server-managed OpenAI fallback as configured without exposing its value. A per-user encrypted OpenAI key overrides this fallback.

Google incremental scopes: `openid email`, Calendar read/write, Contacts read, Gmail read/compose/send. Microsoft delegated scopes: `openid profile email offline_access User.Read Calendars.ReadWrite Contacts.Read Mail.Read Mail.ReadWrite Mail.Send OnlineMeetings.ReadWrite`.

All calls have explicit timeouts. OAuth state is one-time. External writes require a confirmed pending action and read-after-write verification.
