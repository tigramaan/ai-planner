# INTEGRATION_HANDOVER: UMEC AI Planner

## Required owner actions

1. Set a strong bootstrap administrator password, family registration code and 32-byte master key in the production secret store.
2. In Google Cloud create a Web OAuth client with callback `https://planner.umec.space/api/v1/integrations/google/oauth/callback`; enable Calendar, People and Gmail APIs.
3. In Microsoft Entra create a Web app with callback `https://planner.umec.space/api/v1/integrations/microsoft/oauth/callback`; allow delegated Graph permissions listed in `contracts/integration-service.md`.
4. Sign in as `tigramaan@gmail.com`, invite family members with the registration code, and let each user connect their own Google/Microsoft accounts from Settings.
5. Run the live acceptance checklist with sandbox contacts only.

OpenAI API billing is managed separately from ChatGPT subscriptions. Production uses the existing server API key; configure project usage limits and alerts in the OpenAI Platform billing settings because ChatGPT Plus/Pro credits cannot be applied to API traffic.

Provider client secrets and OAuth tokens are runtime data. They must never be committed.
