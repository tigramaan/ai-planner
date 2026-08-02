# AGENTS.md - aiplanner Execution Manual

## Language

All project communication with the user is in Russian. Files with Russian text must be UTF-8.

## Source of Truth

This project is Spec-Driven. Code is not the only source of truth. Requirements, contracts, ADR, runbooks and tests are authoritative.

Required documents:

- specs/SYSTEM_SPEC.md
- specs/EXECUTION_PLAN.md
- specs/TASK_INDEX.md
- specs/TASK_CONTRACT_MATRIX.md
- specs/TRACEABILITY_MATRIX.md
- specs/VERIFICATION_RUNBOOK.md
- specs/INTEGRATION_HANDOVER.md
- docs/adr/*
- docs/catalog/*
- contracts/*

## Mandatory Architecture

The project must use microservice architecture.

Backend code must live under services/*.
Each service must have:

- README.md
- explicit public contract
- health endpoint or health procedure
- config schema
- tests
- deployment notes
- clear ownership of data and side effects

Forbidden:

- god files
- hidden cross-service dependencies
- direct cross-service imports without a contract
- business logic in UI
- direct I/O from domain modules
- undocumented retries or fallbacks

## File Size Guard

No source file may exceed 500 lines.

Run before delivery:

    node tools/guards/check-file-lines.mjs

Generated, vendored and build files are excluded by the guard.

## Guards-First Development

Every boundary must validate input, state, permissions, resources, external API responses and timeout behavior before executing business logic.

## Delivery

Before final delivery update specs/VERIFICATION_RUNBOOK.md and run the available guards/tests.
