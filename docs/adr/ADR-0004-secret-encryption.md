# ADR-0004: Secret encryption

Integration credentials use AES-256-GCM with a unique nonce and provider-bound associated data. A 32-byte master key is supplied through a runtime secret. Plaintext is never returned after write and never enters logs or audit details.
