# Services Catalog

| Service | Purpose | Contract | Health | Status |
| --- | --- | --- | --- | --- |
| api | Auth, integrations, agent, planner data and server-to-server lead booking | `contracts/auth-service.md`, `integration-service.md`, `agent-service.md`, `planner-service.md`, `booking-api.md` | `/health/live`, `/health/ready` | MVP |
| web | Responsive protected PWA | `contracts/web-service.md` | Next process health | MVP |
| worker | Reminder/Web Push delivery and retry | `contracts/planner-service.md` internal worker contract | Redis heartbeat | MVP |

Data ownership: API owns PostgreSQL records and external side effects. Web owns no business data. Worker consumes scheduled delivery work and does not accept public traffic.
