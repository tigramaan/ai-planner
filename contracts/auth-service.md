# Auth Service Contract

Base: `/api/v1/auth`. JSON endpoints: `POST /setup`, `/register`, `/login`, `/refresh`, `/logout`, `/change-password`; `GET /setup-status`, `/api/v1/me`. Initial setup is single-use, requires a high-entropy server token and creates `tigramaan@gmail.com` as administrator. Registration requires the server-side family invitation code. Success sets HttpOnly access/refresh cookies. Password change requires the current password and revokes all sessions.
