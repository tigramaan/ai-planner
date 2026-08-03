# Planner Service Contract

Authenticated endpoints provide local tasks, timers, reminders, per-user Web Push subscriptions, pending actions, Today aggregation and audit. Mutations validate ownership and state. Push endpoints are encrypted at rest and never return subscription secrets. Confirm is idempotent; an expired, cancelled or already executed action cannot execute again.

The worker-only reminder contract requires `X-Worker-Token`. Claiming uses row locking with skip-locked semantics and a processing lease. Completion accepts only delivered, retry, or failed state transitions; retries use a bounded exponential delay. Provider payloads are released only to the authenticated worker and only for the reminder owner.

Pending calendar changes cover `update_event`, `cancel_event` and `add_event_participants`. The encrypted payload binds the provider event ID, original event snapshot and requested mutation before confirmation. Confirmation revalidates ownership through the user's provider token and executes the immutable mutation once.
