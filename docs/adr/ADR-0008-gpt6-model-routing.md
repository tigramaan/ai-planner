# ADR-0008: GPT-6.1 Sol with two reasoning tiers

Date: 2026-10-07. Status: accepted. Requirements: REQ-021, REQ-069–REQ-072.
Task: AP-019.

Context: the owner requested stronger family-6 models instead of GPT-5.6 Luna/Sol,
approved reuse of the existing server API key, and explicitly excluded Astra.

Decision: use GPT-6.1 Sol for planner, junior and senior roles. Junior/planner keep
low reasoning; senior uses medium. Preserve the semantic router, separate role
configuration and distinct reasoning efforts. Align new-secret and Web defaults;
preserve saved user models and key material. Keep Responses, schema, prompts,
timeouts/retries, six-round sequential tool limit and confirmation unchanged.

Alternatives: GPT-6 Luna retains the efficiency tier the owner wants to replace.
GPT-6 Astra is explicitly excluded by the owner. Removing routing and applying one
effort to all requests would discard the existing fast/complex behavior split.

Trade-offs: stronger default interpretation increases token costs; medium reasoning
is reserved for escalated work. Tier differentiation comes from reasoning effort,
task shape and senior tool access rather than different model IDs. Measure latency
in controlled checks. Existing per-user mail model overrides remain valid.

Consequences: public v1 payload schemas stay compatible; no database migration is
needed. Existing credentials are reused without logging or replacing them. Verify
strict output and bounded tools before rollout. Retain prior API/Web images and
model settings for rollback.

Official references:
- https://developers.openai.com/api/docs/models/gpt-6.1-sol
- https://developers.openai.com/api/docs/guides/latest-model
