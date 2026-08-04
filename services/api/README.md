# API service

Owns authentication, encrypted integrations, agent orchestration, local planner data, audit and the server-to-server booking boundary. Public contracts are under `contracts/`, including `booking-api.md`. Health: `GET /health/live` and `/health/ready`.

Booking API keys are created by an authenticated owner, displayed once and persisted only as hashes. The website calls `/booking/v1/*`; contact data is encrypted and provider writes are rechecked and read back.

## Development

`python -m uvicorn app.main:app --reload`. Configuration is validated from environment by `app.config.Settings`. Run `pytest` and `ruff check .`.

## Deployment

Run the image as a non-root user behind the gateway. Supply database, master key, JWT secret and provider credentials through Docker secrets/environment. Apply `alembic upgrade head` before traffic.
