# ADR-0002: Stack and PWA

## Decision

Use FastAPI/Pydantic/SQLAlchemy for the API, PostgreSQL and Redis for state, Next.js/TypeScript/Fluent UI for the installable PWA, and a separate worker service for scheduled delivery.

## Rationale

PWA validates the Android workflow before maintaining a native shell. Services remain separately deployable and communicate through documented contracts.
