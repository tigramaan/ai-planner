# Security policy

## Reporting a vulnerability

Do not open a public issue for suspected credential exposure, authentication bypass, BOLA/IDOR, token leakage or remote code execution. Use GitHub's **Security → Report a vulnerability** private advisory for this repository and include affected version, reproduction steps and impact. Do not include real user data or production secrets.

## Secret handling

Only `.env.example` with placeholders belongs in Git. Keep `.env`, `.secrets/`, private keys, OAuth client secrets, database dumps and backups outside version control. If a credential is ever committed, revoke and rotate it first; removing the file in a later commit is insufficient because Git retains history.

CI scans the complete Git history with Gitleaks. Provider tokens are encrypted at rest, but repository contributors must still use test tenants and synthetic contacts for validation.
