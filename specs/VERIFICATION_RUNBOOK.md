# VERIFICATION_RUNBOOK: UMEC AI Planner

## Automated gates

Run from repository root:

1. `.venv/bin/ruff check services/api`
2. `.venv/bin/pytest services/api --cov=services/api/app --cov-report=term-missing`
3. `npm run worker:test`
4. `npm run web:test`
5. `npm run web:build`
6. `docker compose --env-file .env.example config -q`
7. `node tools/guards/check-file-lines.mjs`
8. `git diff --check`

Latest local result (2026-08-03): ruff passed; API planner suite includes authenticated Today/Week aggregation and anonymous-access rejection. The seven-day view uses the same guarded provider collector as Today, and Gmail 401/403 failures return localized reauthorization guidance rather than a raw upstream error. Calendar events apply the per-user reminder offset (five minutes by default), and an explicit Telemost/Yandex request overrides stale Teams context. Chat history is limited to the latest 50 messages in chronological order and the Web viewport follows new messages unless the user scrolls upward. Provider defaults, explicit-only video creation, Zoom OAuth/meeting verification, encrypted recipient aliases, encrypted Teams/Telemost fallback rooms, strict fallback URL allowlisting, partial calendar success when video creation fails, conversation continuation, calendar mutations, provider guards, browser audio and untrusted-host rejection passed. Russian/English browser-locale resolution, Next production build, Compose config, line guard and diff check passed. Production Python images require patched pip 26.1.2 and cryptography 48.0.1 or newer; development tooling requires patched pytest 9.0.3 or newer. npm audit retains three high advisories in dependencies bundled by Next.js 16.2.12; the application does not accept external CSS or image uploads, and npm currently offers only an invalid breaking downgrade rather than a safe fix. Migration upgrade/downgrade/upgrade passed through the reminder preference. Production smoke, VAPID access, Nginx security headers, auth/AI rate limits and all service health checks passed. A checksum-verified production backup restored 11 tables into a disposable database and was removed after the drill.

Cross-account security acceptance (2026-08-03): a second family member cannot list, update, delete, confirm or cancel the first member's tasks, timers, pending actions, reminders, chat, integrations, preferences, audit or agenda data. Foreign object identifiers return 404, encrypted fallback links remain private, a signed access token with a session belonging to another subject is rejected with 401, and public setup status does not reveal the administrator email.

Mobile chat acceptance (2026-08-03): the composer occupies the full chat width, expands from one line with typed, drafted or transcribed text up to 240 px, then scrolls internally. Microphone and send controls sit in a separate bottom action row and retain at least 50 px touch targets on mobile. Ctrl/Cmd+Enter sends while plain Enter creates a new line.

Flexible calendar lookup acceptance (2026-08-03): update/cancel/participant actions match partial titles, inflected participant names and attendee addresses. An inferred current time only ranks candidates and never filters out a strong name match. Multiple or weak matches are shown as numbered choices with local date/time, and a numeric follow-up reconstructs the unfinished action.

External action reporting acceptance (2026-08-03): meeting creation, event update/cancellation, participant addition and email sending always create a pending action with Confirm/Cancel controls. Confirmation by button or chat returns the same localized report with operation, title, local date/time, provider and participants. Calendar and video URLs are retained separately and rendered as clickable HTTPS links; partial video failures explicitly state that the calendar event was still saved.

Persistent session acceptance (2026-08-03): the access cookie lasts one day by default, and its expiry does not send an active user to login. The Web client performs one shared refresh for concurrent unauthorized requests, retries each original operation once, and protected pages remain reachable while the HttpOnly refresh cookie exists. Successful refresh extends the bounded server session without a multi-tab token-rotation race; logout, password change, revocation and refresh expiry still terminate access.

Adaptive logo acceptance (2026-08-03): navigation shows the supplied black UMEC mark on light surfaces and automatically renders the same transparent mark in white when the browser requests a dark color scheme. Switching the system theme updates the mark without a reload; PWA application icons retain their branded artwork.

Gmail OAuth callback acceptance (2026-08-03): Google denial, omitted Gmail permissions and a failed Gmail profile capability check redirect back to Settings with localized recovery instructions. The integration is persisted as connected only after the token's granted scopes cover the request and the Gmail API accepts the access token; a rejected callback never leaves a false connected record.

OAuth session-return acceptance (2026-08-03): access and refresh cookies are HttpOnly, Secure in production and SameSite=Lax. OAuth start reissues an existing session with the compatible attribute before leaving the site, so pre-fix browser sessions are repaired without another login. A top-level GET redirect from Google/Microsoft/Zoom retains the application session and reaches Settings rather than Login; cross-site POST requests still do not receive the cookies. OAuth state remains single-use and user-bound.

Family invitation and logout acceptance (2026-08-03): navigation provides an explicit logout action that revokes the current refresh session before returning to login. Every authenticated member can create and copy unlimited high-entropy invitation URLs from Settings; raw tokens are never stored, each expires after seven days and registers exactly one isolated non-admin account. Invite replay returns forbidden.

Public project acceptance (2026-08-03, updated 2026-08-04): Gitleaks reports zero findings across repository history and the README, Pages, skill, workflows and security policy. CI checks out full history and blocks future leaks. The responsive GitHub Pages landing is text-led, renders from 320 to 1440 px, leads with self-hosting and owner-controlled access, distinguishes personal, family and small-company use, covers Web/PWA, voice, tasks, timers, agenda, mail analysis, calendar, push, commitment radar, security, installation and provider support, and uses no decorative product mockups. The repository `deploy-aiplanner` skill passes the official skill validator and explicitly prevents secret disclosure while configuring OpenAI, Google, Microsoft, Zoom, Yandex 360 and web push.

Additional UI acceptance (2026-08-03): Today/Week show start/end, timer trigger, attendees, reminders, safe meeting links, provider edit links, task completion/deletion, timer restart/deletion and calendar change/cancel drafts. PWA installation supports the browser prompt plus iOS/Android fallback instructions, with UMEC-branded manifest and Apple icons. Tasks support description, Moscow due date, priority, search, status/date filters, completion/reopening, inline editing, collapsed completed work and confirmed deletion; mutation endpoints enforce per-user ownership. Chat/voice support detailed task creation, update, completion, reopening and deletion plus timer restart/deletion. Command examples cover these mutations and open as chat drafts. Explicit Telemost selection overrides stale video context for both new and updated events, and a configured permanent room is written into the calendar event.

## Migration drill

Against a disposable database, run `alembic upgrade head`, `alembic downgrade base`, then `alembic upgrade head`. Never downgrade production without a backup and reviewed migration.

## Backup drill

The `backup` service creates a custom-format `pg_dump`, validates its catalog, writes SHA-256 and retains 14 days. Restore only into an empty disposable database first using `infra/backup/restore.sh`; verify schema and row counts before scheduling a production maintenance window.

## Live provider acceptance

Use sandbox contacts only. For each family member:

1. Create multiple member invite links, register through one, verify it cannot be reused, and verify another member's tasks/integrations are absent.
2. Create a task with a due date and priority; edit, complete, reopen and delete it, then verify a second user cannot mutate it.
3. Save an OpenAI key, transcribe a voice sample, and verify no key appears in API/log/audit output.

OpenAI latency acceptance (2026-08-03): the default planner model is `gpt-5.6-luna`; intent extraction sends explicit `reasoning.effort=low` through the Responses API. Unit tests must assert the reasoning request contract, while existing structured-intent and conversation tests guard behavior.

Gmail natural-search acceptance (2026-08-03): authorize Gmail read access, then verify «непрочитанные письма за сегодня» maps to `is:unread` plus local-day bounds and «письма от <имя> с документами» maps to sender plus attachment filters. Confirm the real mailbox returns the same records as Gmail UI without exposing tokens or message bodies in logs.

Gmail summary acceptance (2026-08-03): explicitly request a summary for a matching message with TXT/HTML/CSV/PDF/DOCX/XLSX attachments. Verify the response identifies the message, lists processed attachment names, reports facts/prices/deadlines, caps attachments at five and total input at 20 MiB, and sends extracted content to OpenAI only for that explicit request with `store=false`. OAuth tokens, raw content and attachment bytes must not appear in application logs or audit records.

Public/privacy and feedback acceptance (2026-08-03, updated 2026-08-04): README and Pages contain no product screenshots, mock inboxes or personal data. Public copy describes commitment analysis, mail, calendar, tasks, per-device push and confirmation boundaries without claiming unimplemented automation. `LICENSE` contains MIT terms. Creating/copying an invite and successful task, agenda, settings and push actions surface a localized `role=status` notification that disappears automatically and remains above mobile navigation.

Public page copy acceptance (2026-08-04): verify README and Pages describe the complete implemented product rather than centering one AI feature, lead with self-hosting and sensitive-data ownership, explain that commitment analysis is explicit and read-only, distinguish push-service acceptance from operating-system display, and state that external writes require confirmation. At 320, 390, 768 and 1440 px, verify there is no horizontal overflow, navigation and CTA labels remain usable, light/blue/dark section alternation is visually clear, and every button/text pair retains readable contrast under both system themes.

Gmail compose/send acceptance (2026-08-03): ask the agent to write a polite email from a communication goal. Verify it produces a complete subject and body without invented facts, resolves a unique recipient, refuses to prepare a send action without Gmail compose/send scope, and shows the exact recipient, subject and body before Confirm/Cancel. Confirmation performs Gmail send and a metadata read-back; cancellation and automated tests never contact a real recipient.

Timer notification acceptance (2026-08-03): enable browser push in Settings, start a one-minute timer in chat, and verify exactly one linked reminder is scheduled for the timer end. Restart it and verify the same reminder moves; rename it and verify the notification text changes; delete it and verify delivery is removed. At expiry, verify the service worker displays the push while the PWA is backgrounded. Without a subscription, chat must show setup guidance and the worker must retry without recording a false delivery. Today/Week must show the timer only once.

Task and notification-state acceptance (2026-08-03): create an open task with a future due time and verify exactly one linked push reminder. Change the due time, rename, complete, reopen and delete it; verify move, text update without repeat, removal, restoration and final removal respectively. Existing future tasks are backfilled. Every authenticated screen shows whether this browser is checking, enabled, off, blocked, unsupported or failed; Enable is an explicit click, blocked permission explains browser-site recovery, and no API response contains a push endpoint or key. Creating a due task or timer without a subscription must report success plus an actionable notification warning.

Mobile chat viewport acceptance (2026-08-03): at 360x640, 390x844 and 430x932 CSS-pixel viewports, verify the chat page has no hero heading or command-example panel, the browser document does not vertically scroll, bottom navigation and the complete composer remain visible, and long history scrolls only inside the message list. Repeat with the notification banner visible and with a multi-line composer value; neither may push the composer behind navigation.

Mail triage acceptance (2026-08-03): request today's emails that actually require attention while excluding newsletters, spam and noise. Verify no more than twenty bounded metadata rows are sent to the model with `store=false`; email fields are explicitly untrusted; the answer contains only action-required and important-to-read messages, gives a metadata-grounded reason and next step for each, reports the ignored count, and performs no Gmail mutation. Generic promotions, newsletters, webinar invitations, routine receipts and product announcements without an issue must be ignored by default.

Semantic agent freedom acceptance (2026-08-03): express search, single-message explanation and inbox prioritization through several indirect Russian and English paraphrases that contain none of the implementation's prior marker words. Verify the model selects `mail_mode=search|summarize|triage` from meaning, no application keyword list participates in routing, and the same deterministic permission, size, confirmation and provider-response guards apply after strategy selection.

Junior/senior router acceptance (2026-08-03): verify a clear one-operation command is interpreted once by `gpt-5.6-luna` with low reasoning. Verify novel, unknown, ambiguous, strategic and multi-operation goals produce a bounded junior escalation and are reinterpreted by `gpt-5.6-sol` with medium reasoning. Routing must not inspect application keyword lists; audit stores only the selected tier. Provider permissions and confirmation policy are identical for both tiers.

Senior tool-loop acceptance (2026-08-03): issue a compound request that requires mail inspection followed by a local task. Verify Sol calls the bounded mail tool, receives its real output, then calls the local planner tool and reports only completed effects. The Responses requests use `store=false`, sequential calls and at most six rounds. Invalid arguments become bounded tool errors; secrets never enter model/tool payloads; external email/calendar writes are not executed or claimed by this loop.

Senior confirmation-boundary acceptance (2026-08-03): issue a compound request that inspects mail and then prepares a reply or calendar change. Verify the loop creates at most one encrypted pending action, returns its identifier to chat for Confirm/Cancel controls, and reports it only as awaiting confirmation. Recipient resolution, Gmail send scope, calendar matching and payload validation run before creation. Verify no provider mutation occurs until the existing confirmation endpoint executes it with read-after-write validation.

Chat wait-state and strict mail importance acceptance (2026-08-03): submit a chat command with an artificially delayed response and verify an accessible localized typing indicator appears in the message stream, remains visible and pinned while waiting, then disappears on success or failure. Request exactly three important emails from a mixed inbox. Verify `mail_limit=3`, no more than three results, and deterministic exclusion of no-reply, List-Id/List-Unsubscribe, bulk/list/junk precedence and auto-submitted messages before model ranking. Only human-authored personal or work messages may remain.

Push delivery recovery acceptance (2026-08-04): production reminder failures were traced to `push:PermissionError`: the non-root worker could not read the host-mounted VAPID private key while browser permission and subscription were valid. Set the key to mode `0640`, set `VAPID_FILE_GID` to its numeric host group, recreate the worker and verify that the supplementary group can read the mounted key. The worker must refuse to start before heartbeat when access is absent. Requeue one failed one-minute timer and verify the real push changes to `delivered` on the first attempt. In the Web UI press **Проверить** and verify the test endpoint creates an owned immediate reminder, the worker reports delivery, and no endpoint or encryption key is returned to the browser status response.

Named timer chronology acceptance (2026-08-04): start overlapping one-minute timers named «Макароны» and «Яйца». The two assistant acknowledgements must repeat the correct name, duration and local end time. Every existing and new chat bubble shows a compact localized `HH:MM` timestamp. When each push is delivered, its timer changes from active to finished and exactly one assistant history entry with that timer name and delivery time appears through background synchronization without reloading the page.

Per-device push and commitment-radar acceptance (2026-08-04): with two browser subscriptions, make one endpoint fail and verify the successful endpoint does not hide its failure; retries exclude an already accepted endpoint, and `404/410` removes only the stale subscription. From each device, Settings test must target its own subscription and identify push-service acceptance without claiming OS display. On iOS Home Screen PWA, verify the Declarative Web Push payload is displayed while closed. In «Контур», run an explicit 30-day check and verify at most 15 incoming plus 15 sent metadata rows are processed with no model storage, findings cite a real source index, task/calendar coverage is shown, and «Разобрать» only fills a chat draft.

Booking API acceptance (2026-08-04): enable booking in Settings, connect Google Calendar, select the booking VKS default, and configure work hours, duration, buffers, notice, horizon and daily limit, then create a website key. Verify plaintext is returned once and subsequent settings contain only its prefix/metadata. From a backend client, fetch availability in a valid IANA timezone and create a meeting with attendee email plus `Idempotency-Key`; verify Google read-back and invitation. Repeat the identical request and verify no second event. Occupy a Google slot and verify `slot_unavailable` does not consume an attempt. Create three successful meetings for one stable `lead_id`; the fourth must return `booking_attempt_limit_reached`. Revoke the key and verify both availability and booking return `401`. Confirm contact data is encrypted and no token/contact body appears in audit or logs. Run API/Web suites, production build, Alembic single-head/migration drill, line guard and `git diff --check`.

Booking API local verification (2026-08-04): booking tests passed for one-time key display, revocation, Google conflict handling, idempotent replay and the three-success `lead_id` limit; the complete API suite passed. Ruff, all 21 Web tests and the Next.js production build passed. Alembic has one head and the complete PostgreSQL chain passed upgrade -> booking downgrade -> upgrade in a disposable database. Live Google invitation delivery remains an explicit provider acceptance step.

Shared task acceptance (2026-08-04): create users A, B and C on one server. A shares a task with B by exact email; B sees it in Tasks and Today/Week, edits its description, adds and completes checklist items, and sees bounded author/timestamp history. Verify B cannot add C or delete the task, but can leave it. Verify A can revoke B and delete the task, unshared users receive not-found, no user directory/public link exists, and owner reminders remain owned by A. Run collaboration/isolation tests, full API/Web suites, production build, PostgreSQL migration drill, line guard and diff check.

Shared task local verification (2026-08-04): collaboration tests passed owner/member/third-user permissions, shared Tasks and Today visibility, checklist validation/editing, member leave, owner revoke, activity attribution and delete isolation. The complete API suite, Ruff, TypeScript, all 21 Web tests, Next.js production build and file-line guard passed. The complete PostgreSQL migration chain passed upgrade -> shared-task downgrade -> upgrade in a disposable database.

Shared task chat-edit regression (2026-08-05): as a participant, edit and complete a shared task by its title through chat and verify the owner sees the change with the participant recorded in activity. Reopen it and verify any due-time reminder remains owned by the task owner. A participant's chat request to delete the task must be rejected without mutation. Run collaboration tests, the complete API suite, Ruff, Web tests/build, line guard and `git diff --check`.

Booking/shared-task production deployment (2026-08-04): a validated custom-format backup with checksum was created before migration. API, Web and worker images rebuilt; production Alembic advanced through booking to shared-task head `a92d0c5e7b31`. API, Web, worker, PostgreSQL, Redis and backup services are healthy. Internal and externally proxied readiness returned `200`, the public Web root loaded, and unauthenticated Tasks access returned `401`. The host already uses an external reverse proxy on port 80, so the optional Compose Caddy profile was not retained.

Google-only booking/VKS verification (2026-08-04): booking settings expose Google Meet, Yandex Telemost, Zoom and no-video defaults. Tests set the general calendar default to Microsoft and verified availability plus creation still call only Google; the selected Telemost URL is placed into the Google event. Full API suite, Ruff, 21 Web tests, TypeScript/Next production build and PostgreSQL upgrade -> VKS downgrade -> upgrade passed.

Recipient relevance/click acceptance (2026-08-10): resolve a reversed Cyrillic contact name and its Latin spelling across a later Google Contacts page. Verify the saved/contact address is retained, unrelated Gmail search senders plus `no-reply`, sales and Redmine addresses are excluded, and no more than three strong candidates are shown. Two real addresses with the same matching sender identity require clarification; a weak partial name asks for the email instead of guessing. Click each candidate in chat and verify it is inserted into the focused composer without automatic submission. Run recipient/contact adapter tests, Web Chat tests, full API/Web suites, production build, line guard and `git diff --check`.
4. Authorize Google Calendar/Contacts, then Gmail read/compose/send incrementally.
5. Authorize Microsoft Calendar/Contacts/Teams, verify granted scopes.
6. Create a pending meeting action; cancel once and confirm a new one once.
7. Verify read-after-write result, meeting URL, participant invitation and audit record.
8. Change password and verify prior sessions are rejected.

Real OAuth acceptance requires provider consent for every production account.

## Security audit

Run the automated gates above, then verify the deployed boundary:

1. Anonymous requests to `/api/v1/me`, chat, planner and integration APIs return `401`.
2. Cross-origin preflight from an unlisted origin is rejected and untrusted `Host` values return `400`.
3. TLS is valid; HSTS, CSP, `nosniff`, referrer and permissions policies are present.
4. Login/setup/register and AI/voice routes have separate Nginx request limits.
5. `.env`, private keys and backups are ignored by Git and inaccessible to other host users.
6. API, Web and worker containers run as non-root; Postgres and Redis have no published ports.
7. OAuth state is hashed, expires after ten minutes, is provider-bound and single-use; provider tokens and pending actions are AES-GCM encrypted with context binding.
8. Calendar/mail writes require an immutable pending-action confirmation and provider read-after-write verification.
9. Rotate any provider credential disclosed outside the production secret store, then revoke the superseded value.
## REQ-076 — Живые таймеры и голосовая автоотправка

1. Запустить параллельно таймеры «Макароны» и «Яйца» и убедиться, что обе карточки показывают свои названия и независимый обратный отсчёт.
2. Дождаться завершения: активная карточка должна исчезнуть, в истории должно появиться обычное сообщение «Таймер … завершён» со временем.
3. Произнести короткую команду и замолчать минимум на 1,4 секунды: запись должна остановиться, команда — отправиться автоматически.
4. Произнести длинный составной запрос: после паузы расшифровка должна остаться в поле ввода для редактирования.
5. Запустить `npm run web:test`, `.venv/bin/pytest services/api/tests/test_planner.py -q`, `npm run web:build` и `npm run guards`.
## REQ-077 — Desktop viewport и хранение чата

1. Открыть чат на desktop: страница не должна прокручиваться, composer остаётся видимым, прокручивается только история.
2. Свернуть левое меню и перезагрузить страницу: состояние панели иконок должно сохраниться.
3. Уменьшить ширину ниже 1100 px: примеры команд должны исчезнуть, а чат занять освободившееся место.
4. При включённых уведомлениях плашка в чате отсутствует; при выключенных появляется предупреждение, а включение и тест доступны в настройках.
5. Навести указатель на сообщение: дата и время плавно раскрываются без системного tooltip.
6. Убедиться автоматическим тестом, что сообщение старше 100 дней удаляется, а новое остаётся.
7. Запустить полный API/Web test suite, production build, line guard и `git diff --check`.

## REQ-078 — Архив задач и chat-only таймеры

1. Завершить задачу и открыть вкладку «Архив»: задача должна сохраниться там и не отображаться среди открытых.
2. Вернуть архивную задачу в работу: она должна исчезнуть из архива и появиться среди открытых.
3. Запустить таймер и проверить API/экраны «Сегодня» и «Неделя»: таймера там быть не должно.
4. Проверить чат: активный таймер показывает обратный отсчёт, а после завершения остаётся обычное чат-сообщение; отдельного архива таймеров нет.
5. Запустить `pytest services/api/tests/test_planner.py`, Web tests/build, line guard и `git diff --check`.

## REQ-060 — Диагностика Gmail OAuth

Если Google выдал все запрошенные Gmail scopes, но проверка профиля почтового ящика
возвращает ошибку, callback не сохраняет интеграцию и показывает отдельную рекомендацию
завершить настройку Gmail. Сервер журналирует только HTTP-статус и безопасный код причины
провайдера; OAuth-токены, адреса и тело ответа в журнал не попадают.
Отказы до проверки Gmail журналируются только как фиксированное название этапа callback.
Google может не повторить `openid`/`email` в поле `scope` token response после incremental
consent. Прикладные scopes остаются обязательными, а identity проверяется живым запросом
профиля до сохранения интеграции.

## REQ-079 — Мобильная ширина всех разделов

1. Проверить Чат, Сегодня, Неделю, Задачи и Настройки на ширинах 320, 360 и 390 px:
   документ не должен иметь горизонтальной прокрутки, а панели не должны выходить за viewport.
2. На экране Задач проверить создание, фильтры, поиск, длинное название и редактирование:
   поля с датой не расширяют сетку, фильтры переносятся, действия остаются доступны.
3. На экранах Сегодня и Неделя проверить длинные ссылки, участников и кнопки событий:
   текст переносится, кнопки занимают доступную ширину.
4. В Настройках проверить интеграции и уведомления: строки и кнопки складываются вертикально.
5. Запустить Web tests/build, line guard и `git diff --check`.
