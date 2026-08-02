# ADR-0001: Microservice Architecture

## Context

The project is provisioned for independent services, explicit contracts and replaceable components.

## Decision

Use microservice architecture under services/* with contracts under contracts/*.

## Consequences

Every service must define its own responsibility, public contract, health check and tests.
