# API service

Owns authentication, encrypted integrations, agent orchestration, local planner data and audit. Public contract is under `contracts/`. Health: `GET /health/live` and `/health/ready`.

## Development

`python -m uvicorn app.main:app --reload`. Configuration is validated from environment by `app.config.Settings`. Run `pytest` and `ruff check .`.

## Deployment

Run the image as a non-root user behind the gateway. Supply database, master key, JWT secret and provider credentials through Docker secrets/environment. Apply `alembic upgrade head` before traffic.
