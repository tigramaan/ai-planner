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
| REQ-041..044 | provider preferences, explicit conference intent, partial success, Zoom OAuth/meeting adapter, Yandex eligibility guard and encrypted permanent-room fallbacks | preferences, intent, confirmation fallback, OAuth, URL validation, encryption and adapter tests |
| REQ-045 | bounded chat-history query and bottom-pinned Web chat viewport | chat-history API test, Web tests and production build |
| REQ-046 | per-user calendar reminder preference and deterministic explicit conference override | preference, adapter, summary and conference-intent tests |
| REQ-047..048 | shared bounded agenda collector, Week Web route and localized mail-provider recovery | planner/API auth tests, Web build and provider-error tests |
| REQ-049..050 | normalized agenda metadata, safe provider links, chat correction draft and PWA install surface/icons | agenda unit test, manifest test and Web production build |
| REQ-051 | task creation, search/filtering, inline editing, completion/reopening and deletion | task lifecycle and ownership API tests, Web production build |
| REQ-052..053 | local planner mutations, Telemost update override, agenda controls, interactive examples and UMEC logo assets | conversation, calendar action, planner and Web/manifest tests |
| REQ-005..006, REQ-054 | per-user ownership filters, session-subject binding and foreign-object not-found guards | cross-user BOLA isolation, auth and OAuth state tests |
| REQ-055 | full-width auto-growing chat composer with a separate mobile action row | Web production build and mobile UI acceptance |
| REQ-056 | ranked fuzzy calendar lookup across titles and attendees with numbered disambiguation | calendar action and conversation tests |
| REQ-057 | mandatory external-write confirmation and structured post-execution reports with separate links | action policy, summary, calendar mutation and Web build tests |
| REQ-058 | transparent Web access-token refresh, retry, refresh-cookie route admission and sliding server session | auth refresh, API client and proxy tests |
| REQ-059 | adaptive black/white navigation logo selected by the browser color scheme | Web production build and visual acceptance |
| REQ-060 | granted-scope and live Gmail validation before OAuth persistence with localized callback recovery | OAuth callback tests and Web production build |
| REQ-061 | explicit session-revoking logout and admin-only, hashed, expiring single-use family invites | auth/family permission and replay tests, migration drill and Web build |
| REQ-062 | public README/Pages/screenshots, security policy, Gitleaks CI and deploy-aiplanner skill | Gitleaks history/tree scans, skill validator, static-page visual review and CI |
| REQ-030..035 | password, cipher, OAuth state, redaction | security tests |
| REQ-036 | recipient resolver and Google/Microsoft contact adapters | recipient and adapter unit tests |
| REQ-037 | bounded per-user conversation history passed to intent extraction | conversation continuation tests |
