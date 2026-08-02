# UMEC AI Planner

Self-hosted family command center for calendars, mail, tasks, timers and AI-assisted text/voice commands. Every family member has an isolated account, integrations, encrypted secrets, messages and audit history.

## Local verification

```bash
python3 -m venv .venv
.venv/bin/pip install -e 'services/api[dev]'
npm install
.venv/bin/ruff check services/api
.venv/bin/pytest services/api
npm run web:test
npm run web:build
node tools/guards/check-file-lines.mjs
```

## Deployment

Copy `.env.example` to a protected runtime `.env`, replace every placeholder, register provider callback URLs described in `specs/INTEGRATION_HANDOVER.md`, then run `docker compose up -d --build`. Never commit `.env`.

Public domain: `https://planner.umec.space`.
