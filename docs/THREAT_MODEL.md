# Threat model

| Threat | Boundary | Mitigation |
| --- | --- | --- |
| Credential theft | browser/API/database | HttpOnly sessions, Argon2id, AES-GCM, secrets never returned |
| Login brute force | auth endpoint | invite-only registration, generic errors; gateway rate limiting and lockout are required before production |
| CSRF/OAuth replay | cookie/OAuth callback | SameSite Strict, origin checks, single-use expiring state |
| Prompt injection | external content/model | untrusted-data labeling, typed tools, policy gate, no model networking |
| Duplicate writes | retries/providers | idempotency records and read-after-write verification |
| Token leakage | logs/audit/errors | central redaction and safe error mapping |
| SSRF | adapters | fixed provider base URLs and no user-provided request URLs |
| Supply chain | builds | lockfiles, dependency audit and CI tests |
| User lockout | external identity outage | independent local passwords and documented administrator recovery procedure |
| Cross-user data access | API/database/provider tokens | mandatory `user_id` ownership filters, OAuth state binding and isolation tests |
