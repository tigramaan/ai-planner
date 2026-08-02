# Agent Service Contract

`POST /api/v1/chat/messages` accepts text and returns a typed intent, execution status, assistant response and optional pending action. `POST /api/v1/voice/transcribe` accepts bounded audio. Planner model output must match the published JSON schema; invalid output is rejected. The model has no credentials and no direct tools.
