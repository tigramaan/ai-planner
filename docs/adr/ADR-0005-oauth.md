# ADR-0005: OAuth authorization code flows

Google and Microsoft use server-side authorization code flows, offline access, incremental least-privilege scopes, exact HTTPS redirects and single-use CSRF state. Tokens are stored only through the encrypted secret service.
