# J-ROC AI Platform-Wide Agent System

This directory defines the shared agent control plane for J-ROC AI. It is deliberately outside the Android application source tree. Android is one host among Windows, Linux, web, cloud services, repair products, the Factory, the Academy and future J-ROC AI applications.

## Source of truth

- `registry/agent-catalog.json`: canonical platform-wide agent identities, domains and responsibilities.
- `policies/platform-agent-security-policy.json`: mandatory cross-product security, permissions, secrets, approvals and audit policy.
- `templates/agent-manifest.template.json`: reusable manifest contract for every new agent.
- `contracts/agent-runtime-contract.json`: host-neutral request, response, dispatch and lifecycle contract.
- `reusables/`: shared templates and implementation guidance that product teams should reuse rather than fork.

The earlier Android Source Agent foundation remains a host adapter/prototype. The catalog entry `jrocai.source` is the canonical platform identity; the Android implementation must eventually register against this contract rather than define a separate Android-only identity.

## Platform architecture

```text
Chairman Command
      |
Platform Orchestrator
      |
Shared Agent Registry ---- Policy and Permission Evaluator
      |                              |
Capability Discovery          Environment Agent
      |                       (secret references only)
Specialist Agents                    |
      |                         Audit Service
Host Adapters -----------------------+
(Android / Windows / Linux / Web / Cloud / Factory / Academy / Repair)
```

## Required behavior

1. A product discovers agents from the shared registry by capability and supported host.
2. The registry returns only agents in the `available` lifecycle state for execution.
3. The orchestrator checks caller identity, tenant boundary, permissions, dependencies and policy before dispatch.
4. Secrets are resolved by the Environment Agent into short-lived scoped credentials. Agents must not log or persist secret values.
5. Consequential, destructive, financial, production or external-write actions pause for explicit approval unless a narrow standing authorization is configured.
6. Every attempt writes a redacted audit event. Results distinguish proposed, attempted, completed, verified and failed.
7. A host adapter implements the runtime contract. Business logic and agent identity remain independent of Android or any other host.

## Agent lifecycle

`specified -> registered -> available -> degraded -> disabled -> retired`

An agent is not operational merely because it appears in the catalog. It becomes `registered` after manifest and permission validation; it becomes `available` only after its implementation, dependencies, audit integration, readiness checks and required tests are present and verified. Unimplemented catalog entries remain specifications.

## Initial specialist roster

The catalog includes command and orchestration, registry, environment and identity, security and privacy, source and research, knowledge, architecture and planning, product and experience design, frontend/backend/mobile/desktop/API/database engineering, testing/quality/code review/debugging/documentation, build and release operations, observability and recovery, cost governance, model routing, migration, support, Academy, business operations, marketing, commerce, creative production, repair intelligence and authorized device fleet management.

## Implementation sequence

1. Preserve this contract and make the registry loadable by a shared platform service.
2. Implement registry validation and capability discovery.
3. Implement policy evaluation and Environment Agent secret-reference integration.
4. Add persistent, tenant-aware audit storage.
5. Register the existing Source Agent through a host-neutral adapter.
6. Add agent adapters and tests in dependency order; do not mark a catalog entry available until verified.
7. Add Android, desktop, web and service-host integrations without copying the catalog.

## Security and cost boundaries

- No provider key or other secret in source control, application packages, client code or logs.
- Do not execute discovered source code.
- Do not access private repositories without explicit authorization.
- Enforce the platform zero-dollar spending gate; paid services remain disabled unless the Chairman explicitly approves them.
- Keep tenant data isolated and apply least privilege to every agent.
- Never claim an agent, integration, build or test is complete without evidence.

## Current implementation status

This commit establishes the platform-wide catalog, policy and contracts. It does not yet provide a running registry service, policy engine, persistent audit service, live host adapters or fully implemented specialist agents. Those are subsequent implementation tasks and must be tested before agents are marked available.
