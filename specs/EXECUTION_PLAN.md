# EXECUTION_PLAN: UMEC AI Planner

1. **Foundation**: decisions, threat model, service contracts, config, Compose and CI.
2. **Security slice**: family accounts, invite-only registration, password rotation, sessions, per-user encrypted secrets and audit.
3. **Agent slice**: chat, voice transcription, typed intent, policy and pending actions.
4. **Google slice**: OAuth, Calendar/People/Gmail adapters and verification.
5. **Microsoft slice**: OAuth, Graph Calendar/Teams/Mail adapters and verification.
6. **Planner slice**: tasks, reminders, timers and Today aggregation.
7. **PWA slice**: protected mobile-first UI, voice recording and integration management.
8. **Hardening**: unit/integration/E2E tests, secret checks, backup/restore and deployment runbook.

The first production acceptance path is login -> OpenAI configuration -> Google authorization -> voice command -> contact resolution -> immutable confirmation -> verified calendar event -> audit/Today.
