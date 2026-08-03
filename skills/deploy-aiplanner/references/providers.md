# Provider setup reference

Replace `https://planner.example.com` with the user's public HTTPS origin.

## OpenAI

Create a project API key in OpenAI Platform, configure budget alerts and set `OPENAI_API_KEY`. ChatGPT subscriptions do not include API credits. Default planner model is `gpt-5.6-luna` with `OPENAI_REASONING_EFFORT=low`; transcription defaults to `whisper-1`.

## Google

Create a Google Cloud project and OAuth consent screen. Enable Calendar API, People API and Gmail API. Create a Web OAuth client with redirect URI:

`https://planner.example.com/api/v1/integrations/google/oauth/callback`

Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`. In Testing mode add every account under Test users. Gmail scopes can require Google verification for a public production app. After login, authorize Calendar and Gmail separately from Settings.

## Microsoft and Teams

Create a Microsoft Entra app with redirect URI:

`https://planner.example.com/api/v1/integrations/microsoft/oauth/callback`

Set `MICROSOFT_CLIENT_ID`, `MICROSOFT_CLIENT_SECRET`, and the tenant (`common` for multi-tenant personal use). Grant delegated `User.Read`, `Calendars.ReadWrite`, `Contacts.Read`, `Mail.Read`, `Mail.ReadWrite`, `Mail.Send`, `OnlineMeetings.ReadWrite`, `openid`, `profile`, `email`, and `offline_access` as appropriate.

## Zoom

Create a user-managed General App and add:

`https://planner.example.com/api/v1/integrations/zoom/oauth/callback`

Set `ZOOM_CLIENT_ID` and `ZOOM_CLIENT_SECRET`. Use the repository manifest in `docs/zoom-general-app-manifest.json` as a reviewed starting point.

## Yandex 360 and Telemost

Organization Calendar/Mail access uses an eligible Yandex 360 service application through CalDAV/IMAP/SMTP. Telemost REST API is not available to arbitrary personal accounts. For unsupported accounts, store a permanent `https://telemost.yandex.ru/` room in Settings; warn that recipients can reuse it.

## Web push

Generate a VAPID key pair locally. Put the private key under `.secrets/vapid_private.pem`, never Git, and set only the public key as `VAPID_PUBLIC_KEY`.
