# TRACEABILITY_MATRIX: UMEC AI Planner

| Requirement | Implementation | Verification |
| --- | --- | --- |
| REQ-001..005 | auth routes, family invite, OAuth-compatible session cookies, user ownership | auth/isolation and cookie-attribute tests |
| REQ-010..014 | service directories, contracts, Compose | file guard, health tests |
| REQ-020 | web PWA | web build and browser tests |
| REQ-021 | OpenAI adapter and agent route; explicit Luna low-reasoning request | agent and conversation unit tests |
| REQ-022 | Provider-native mail query builder and chat mail-search route | mail query unit tests; live Gmail acceptance |
| REQ-023 | Gmail content adapters, bounded document extraction and non-stored AI summary service | mail document, summary and agent privacy tests |
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
| REQ-061 | explicit session-revoking logout and unlimited member-created, hashed, expiring single-use family invites | auth/family member and replay tests, migration drill and Web build |
| REQ-062 | self-hosting-first Russian README/Pages covering personal, family and small-team use plus the complete product, security policy, Gitleaks CI and deploy-aiplanner skill | Gitleaks history/tree scans, comprehensive copy review, skill validator, static-page responsive review and CI |
| REQ-063 | privacy-safe full-product descriptions, high-contrast alternating section themes, MIT license and accessible transient Web action notifications | public-copy review, contrast and responsive visual review, asset-reference scan, license check and Web tests/build |
| REQ-064 | natural-language email drafting, Gmail send-scope guard, exact-body confirmation and verified Gmail send adapter | agent, action-summary, scope and Gmail adapter tests |
| REQ-065 | one-to-one timer reminder lifecycle, migration backfill, push readiness guidance and no-subscription retry | planner/chat, agenda, migration and worker tests |
| REQ-066 | one-to-one due-task delivery plus browser/server push status and global enable/recovery UI | task lifecycle, push status API, Web tests/build and migration drill |
| REQ-067 | mobile-only chat viewport, hidden desktop guidance and internally scrolling message history | Web production build and phone-viewport visual acceptance |
| REQ-068 | bounded non-stored mail metadata triage and grounded actionable response formatting | agent privacy, triage detection/formatting and chat route tests |
| REQ-069 | schema-declared semantic strategy selection with deterministic execution boundaries | intent-schema, paraphrase strategy and policy tests |
| REQ-070 | Luna junior routing with automatic Sol escalation and distinct reasoning effort | simple/complex route tests, config validation and audit inspection |
| REQ-071 | bounded senior Responses tool loop over mail and local planner contracts | multi-round output propagation, storage, call-limit and tool validation tests |
| REQ-072 | senior external-action preparation routed into the existing encrypted confirmation boundary | senior pending-action propagation, conversation, policy, recipient and calendar-action tests |
| REQ-073 | in-stream chat response status, explicit mail result limit and deterministic automated-mail exclusion | Chat component lifecycle test, intent-schema, mail-summary and mail-chat tests |
| REQ-074 | VAPID startup validation, supplementary container key group and authenticated push delivery test | worker key-permission test, push test lifecycle API test, Web delivery-check test and live one-minute retry acceptance |
| REQ-075 | message timestamps, named timer response and timer-delivery chat event with bounded polling | chat timestamp test, named timer conversation test, worker completion/history test and multi-timer live acceptance |
| REQ-030..035 | password, cipher, OAuth state, redaction | security tests |
| REQ-036 | conservative recipient matcher, paginated Google/Microsoft contact adapters and clickable chat candidates | ranking/junk-exclusion, adapter pagination and Chat insertion tests |
| REQ-037 | bounded per-user conversation history passed to intent extraction | conversation continuation tests |
| REQ-076 | Активные таймеры с обратным отсчётом и адаптивная голосовая отправка | `services/api/app/routers/local_items.py`, `services/web/src/components/Chat.tsx`, `services/web/src/app/globals.css` | `services/api/tests/test_planner.py`, `services/web/src/components/Chat.test.tsx` |
| REQ-077 | Viewport-чат, сворачиваемая навигация, компактные уведомления и retention 100 дней | `services/web/src/components/Shell.tsx`, `services/web/src/app/page.tsx`, `services/web/src/components/PushSetup.tsx`, `services/web/src/components/Chat.tsx`, `services/web/src/app/globals.css`, `services/api/app/routers/chat.py` | `services/web/src/components/PushSetup.test.tsx`, `services/api/tests/test_chat_retention.py` |
| REQ-078 | Архив выполненных задач и исключение таймеров из agenda | `services/web/src/app/tasks/page.tsx`, `services/api/app/agenda.py` | `services/api/tests/test_planner.py`, Web production build |
| REQ-079 | Мобильная ширина всех разделов от 320 px | responsive Web layouts and global overflow guards | Web tests/build and manual viewport acceptance |
| REQ-080 | Адресная Web Push доставка, stale cleanup и Declarative Web Push | push API/model/migration, worker, service worker and settings UI | reminder API, worker and Web push tests plus live iOS acceptance |
| REQ-081 | Неперсистентный контур обязательств по почте, задачам и календарю | commitments agent/router and responsive Web report | commitment grounding/privacy test, API suite and Web build |
| REQ-082 | Server-to-server запись проверенных лидов в Google Календарь с отдельным default ВКС | booking policy/key models, Google availability/booking router, provider adapters, settings UI | booking auth, Google slot conflict, VKS selection, idempotency, three-success limit, API suite and Web build |
| REQ-083 | Совместные задачи внутри одного сервера без назначения исполнителя | participant/checklist/activity models and API, task chat actions, Tasks UI, Today/Week | collaboration Web/chat permissions and isolation tests, API suite, Web tests/build |
| REQ-084 | Консервативный нечёткий поиск задач, самостоятельных напоминаний, таймеров и событий | shared entity matcher, local chat actions and calendar actions | matcher, conversation and calendar-action tests plus full API suite |
