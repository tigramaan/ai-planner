# Planner Service Contract

Authenticated endpoints provide local tasks, timers, reminders, per-user Web Push subscriptions, pending actions, Today/Week aggregation and audit. Task endpoints support creation, editing, completion, reopening and deletion. Timer endpoints support start, restart, rename and deletion. Mutations validate ownership and state. Push endpoints are encrypted at rest and never return subscription secrets. Confirm is idempotent; an expired, cancelled or already executed action cannot execute again.

Every active timer owns at most one internal push reminder. Start creates it, restart or rename resynchronizes it, and timer deletion removes it. The linked delivery is excluded from agenda results because the timer itself is already visible. A missing browser subscription is a retryable delivery condition and is never recorded as successful; chat tells the user where to enable notifications.

Every open local task with a future due time also owns at most one internal push reminder. Due-time changes reset delivery, title-only changes preserve delivery state, completion/deletion removes it, and reopening restores it while the due time remains future. `GET /api/v1/push/status` returns only whether the current user has a stored subscription; it never returns endpoints or encryption keys.

Push delivery is tracked per encrypted browser subscription. A targeted test resolves the current endpoint by its hash and never fans out to another device. The worker retries only pending endpoints, records provider response codes without subscription material, deletes stale `404/410` subscriptions, and derives aggregate reminder state from all per-device outcomes.

The worker-only reminder contract requires `X-Worker-Token`. Claiming uses row locking with skip-locked semantics and a processing lease. Completion accepts only delivered, retry, or failed state transitions; retries use a bounded exponential delay. Provider payloads are released only to the authenticated worker and only for the reminder owner.

Pending calendar changes cover `update_event`, `cancel_event` and `add_event_participants`. The encrypted payload binds the provider event ID, original event snapshot and requested mutation before confirmation. Confirmation revalidates ownership through the user's provider token and executes the immutable mutation once.
