# Agent Service Contract

`POST /api/v1/chat/messages` accepts text and returns a typed intent, execution status, assistant response and optional pending action. `POST /api/v1/voice/transcribe` accepts bounded WebM, Ogg, MP3, WAV and MP4/M4A browser audio. MIME parameters are normalized before validation; Safari audio-only `video/mp4` is accepted. Planner model output must match the published JSON schema; invalid output is rejected. The model has no credentials and no direct tools.

Intent extraction receives at most eight recent messages for the authenticated user, with each message bounded to 2,000 characters. This history is used to merge concise clarification answers and corrections into the latest unfinished request or pending draft. A replacement draft cancels the prior one. Exact affirmative/negative replies confirm or cancel the latest pending action without model interpretation. Standalone commands and executed/cancelled actions are not merged with older context.

For `send_email`, the model converts the user's communication goal into a complete subject and ready-to-send body without inventing facts or commitments. The exact generated text remains an encrypted pending payload and is displayed to the user before execution; the model never receives provider credentials or sends directly.
