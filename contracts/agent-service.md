# Agent Service Contract

`POST /api/v1/chat/messages` accepts text and returns a typed intent, execution status, assistant response and optional pending action. `POST /api/v1/voice/transcribe` accepts bounded WebM, Ogg, MP3, WAV and MP4/M4A browser audio. MIME parameters are normalized before validation; Safari audio-only `video/mp4` is accepted. Planner model output must match the published JSON schema; invalid output is rejected. The model has no credentials and no direct tools.

Intent extraction receives at most eight recent messages for the authenticated user, with each message bounded to 2,000 characters. This history is used only to merge concise clarification answers into the latest unfinished request. Standalone commands and already prepared/completed actions are not merged with older context.
