# Services Catalog

| Service | Purpose | Contract | Health | Status |
| --- | --- | --- | --- | --- |
| api | Auth, integrations, agent, planner data and server-to-server lead booking | `contracts/auth-service.md`, `integration-service.md`, `agent-service.md`, `planner-service.md`, `booking-api.md` | `/health/live`, `/health/ready` | MVP |
| web | Responsive protected PWA | `contracts/web-service.md` | Next process health | MVP |
| worker | Reminder/Web Push delivery and retry | `contracts/planner-service.md` internal worker contract | Redis heartbeat | MVP |

Data ownership: API owns PostgreSQL records and external side effects. Web owns no business data. Worker consumes scheduled delivery work and does not accept public traffic.

Web locale provider (internal): request-initialized ru/en state shared by all views, then browser languagechange; no stored preference. Public icons are SVG/180/192/512 calendar AI assets. Errors and verification: contracts/web-service.md, AP-018; REQ-027/REQ-050.

API model configuration (internal; AP-019, REQ-021/REQ-070): GPT-6.1 Sol low for
planner/junior, GPT-6.1 Sol medium for senior. Depends on the OpenAI Responses
adapter and encrypted per-user key registry. The semantic routing state is audited
as junior/senior; provider/schema failures are explicit. The Settings model field
and omitted-model secret payload default to Sol. See contracts/agent-service.md.
