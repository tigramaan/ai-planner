# ADR-0007 — Request locale and shared browser locale

Date: 2026-10-07. Status: accepted. REQ-027, AP-018.

## Context

The server rendered English unconditionally while independently initialized
client hooks read navigator.languages. A Russian browser could therefore hydrate
different text and attributes than the server; browser language changes were not
observed. The first-supported-language policy and English fallback must remain.

## Decision

Use a bounded Accept-Language resolver for initial request rendering and HTML
lang. Pass that same initial locale into one shared provider. useSyncExternalStore
preserves the server snapshot during hydration, then reads browser preferences
and subscribes to languagechange. API locale uses the same preference resolver.

## Alternatives

Keeping static English HTML and updating only after mount avoids mismatch but
shows English to Russian users initially and without JavaScript. Storing a locale
cookie or manual setting adds state outside the browser-only preference contract.
Suppressing hydration warnings conceals the inconsistency.

## Consequences

HTML pages render per request rather than sharing static English HTML; no user
locale is persisted. Locale input remains bounded and limited to ru/en. All views
share one locale and one browser-event subscription. Cache/versioned application
icons change independently of business data and schema.

The Web image consumes the workspace lock with npm ci and an allowlisted root context. Pin Next to security-patched 16.3.6 in the already deployed 16.3 minor line instead of the accidental 16.4.0 resolved by an unbounded service-only install. This keeps source tests and production builds on the same dependency versions and excludes secrets from Docker build input.
