# ADR-0006: Confirmation policy

Reads and local low-risk creates can execute immediately. Any external write becomes an immutable, expiring pending action. Confirmation verifies the payload hash and idempotency key; changes create a new action.
