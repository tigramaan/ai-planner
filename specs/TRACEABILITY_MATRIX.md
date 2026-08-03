# TRACEABILITY_MATRIX: UMEC AI Planner

| Requirement | Implementation | Verification |
| --- | --- | --- |
| REQ-001..005 | auth routes, family invite, session cookies, user ownership | auth/isolation tests |
| REQ-010..014 | service directories, contracts, Compose | file guard, health tests |
| REQ-020 | web PWA | web build and browser tests |
| REQ-021 | OpenAI adapter and agent route | agent unit tests |
| REQ-022 | Google OAuth/adapter | OAuth state and mocked adapter tests |
| REQ-023 | Microsoft OAuth/adapter | OAuth state and mocked adapter tests |
| REQ-024..026 | policy/pending action/idempotency | policy and confirmation tests |
| REQ-027 | browser locale resolver, bilingual Web/PWA and localized agent route | locale unit tests and Web build |
| REQ-028 | calendar action matcher, pending actions and provider PATCH/DELETE adapters | calendar action and mutation tests |
| REQ-037..038 | bounded chat context, localized action summaries and latest-draft replacement | conversation and action-summary tests |
| REQ-039 | cancelled-draft recovery and independent calendar/conference providers | conversation, agent and calendar mutation tests |
| REQ-040 | encrypted per-user recipient aliases and guarded provider failures | recipient-alias, ownership and confirmation error tests |
| REQ-030..035 | password, cipher, OAuth state, redaction | security tests |
| REQ-036 | recipient resolver and Google/Microsoft contact adapters | recipient and adapter unit tests |
| REQ-037 | bounded per-user conversation history passed to intent extraction | conversation continuation tests |
