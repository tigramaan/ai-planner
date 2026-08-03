# Auth Service Contract

Base: `/api/v1/auth`. JSON endpoints: `POST /setup`, `/register`, `/login`, `/refresh`, `/logout`, `/change-password`; `GET /setup-status`, `/api/v1/me`. Public setup status exposes only whether setup is required and never reveals the administrator email. Initial setup is single-use, requires a high-entropy server token and creates the configured owner as administrator. Registration requires the server-side family invitation code. Success sets HttpOnly access/refresh cookies. Password change requires the current password and revokes all sessions.
