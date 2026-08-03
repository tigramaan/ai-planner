---
name: deploy-aiplanner
description: Securely install, configure, upgrade, or diagnose self-hosted UMEC AI Planner. Use when an agent must prepare a Linux server, generate local application secrets, configure OpenAI, Google, Microsoft Teams, Zoom, Yandex 360 or web push credentials, deploy with Docker Compose/Caddy, verify health, or explain provider setup without exposing credentials.
---

# Deploy UMEC AI Planner

Operate in the cloned repository root. Communicate in the user's language.

## Workflow

1. Read `AGENTS.md`, `.env.example`, `docker-compose.yml`, `specs/INTEGRATION_HANDOVER.md`, and `references/providers.md`.
2. Inspect prerequisites read-only: Linux, Docker Compose, domain/DNS, ports 80/443, Git status and existing `.env` presence.
3. Never display, log, transmit, commit, or place secrets in commands likely to appear in history. Do not read secret values unless required to validate presence. Report only `set`/`missing`.
4. If `.env` is absent, copy `.env.example`; generate JWT, database, worker, setup and encryption secrets locally. Preserve an existing `.env` and ask before replacing any credential.
5. Ask for external provider credentials one provider at a time. Explain exactly where the user obtains each value and the exact callback URL. Read only the relevant section of `references/providers.md`.
6. Set `PUBLIC_BASE_URL`, `CORS_ORIGINS`, `ALLOWED_HOSTS`, and `PLANNER_DOMAIN` to the user's HTTPS domain. Never leave production placeholders.
7. Validate configuration without echoing values. Ensure `.env`, `.secrets/`, private keys and backups are ignored by Git.
8. Run `docker compose --profile caddy config -q`, then `docker compose --profile caddy up -d --build` only after the user has authorized deployment to that server.
9. Wait for all services to become healthy. Check `/api/health/ready`, TLS, security headers, migrations and container non-root users.
10. Guide initial setup, per-user provider authorization and a sandbox create/confirm/read-after-write test.
11. Finish with configured/missing provider names, health status and concrete next action. Never include secret values.

## Safety gates

- Stop if the target host, domain or existing production data is ambiguous.
- Back up PostgreSQL before upgrades that contain migrations.
- Do not delete volumes, databases, backups, `.env` or keys without explicit approval.
- Do not invent provider eligibility. Telemost API requires an eligible Yandex 360 Business organization; otherwise use a validated permanent Telemost URL.
- OpenAI API billing is separate from ChatGPT subscriptions.
- Claude Code is supported as this deployment agent; the application runtime currently uses OpenAI. Describe Anthropic/Ollama/YandexGPT/GigaChat runtime support as contribution work, not an existing feature.
