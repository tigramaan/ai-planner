# Worker service

Owns scheduled reminder delivery and retries. It never accepts public traffic. The worker claims due reminders through the authenticated internal API, delivers encrypted per-user Web Push subscriptions, and falls back to an in-app delivery state when no browser subscription exists. Failed delivery is retried with a bounded exponential delay.

Health procedure validates its Redis heartbeat is newer than 60 seconds. Deployment requires `WORKER_SERVICE_TOKEN`, `VAPID_SUBJECT`, and the VAPID private key mounted at `VAPID_PRIVATE_KEY_PATH`. The API receives only the matching public key and retains ownership of reminder state, encrypted subscriptions, and audit records.

The worker validates that the VAPID key is readable before it starts its heartbeat. The host key must be `0640`, and `VAPID_FILE_GID` must contain its numeric group id so Docker can add that group to the non-root worker process. An unreadable key therefore makes the container unhealthy instead of silently accepting reminders that cannot be delivered.

Each browser subscription is an isolated delivery boundary. Malformed keys and provider-specific failures are reduced to a non-sensitive error class, healthy subscriptions are still attempted, and the worker requests a bounded retry only when every delivery fails.
