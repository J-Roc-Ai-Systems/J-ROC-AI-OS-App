# Waves Six Through Ten — Operational Service Reference

This document records the operational contracts delivered for batches 51–100. These are authenticated backend services backed by the platform SQLite database, audit events, and the existing leased worker queue. They are not claims that every product feature has a finished end-user workflow.

## Wave 6 — Agent workforce and source intelligence (51–60)
- Platform-wide agent registry and fourteen default specialist agents, including the permanent Source Agent.
- Structured source review, repository inspection, source search, change proposal, build verification, test execution, documentation review, dependency audit, security review, repair diagnostics, compatibility review, Academy review, website brand validation, local model discovery, and release validation job types.
- Explicit approval before dispatch; dispatch creates a bounded durable worker queue job.
- Worker capabilities must include agent:<agent-id>. Workers authenticate with their one-time-issued worker credential and use leases, heartbeats, retries, and completion reporting from the existing worker service.
- The agent queue does not execute shell commands or arbitrary code.

## Wave 7 — Developer platform and application factory (61–70)
- Persistent records for software development kit releases, application projects, website projects, workflow definitions, reusable interface components, integrations, application programming interface versions, developer workspaces, dependency reviews, and release plans.
- Workflow and release resources support approval-state transitions. Production release execution remains a separately authorized worker responsibility.

## Wave 8 — Operating system and device intelligence (71–80)
- Persistent records for cross-device operating system services, device enrollments, local model registrations, model routes, accessibility profiles, file indexes, system diagnostics, network profiles, backup manifests, and privacy consents.
- Device enrollment requires explicit owner confirmation.
- Local model registrations accept local runtimes only. Remote paid model execution remains behind the existing zero-dollar spending gate.
- The Android application now has an authenticated Wave 6–10 API client and live platform/agent status refresh using the encrypted gateway token already stored in secure settings.

## Wave 9 — Enterprise operations and cybersecurity (81–90)
- Persistent records for organizations, role assignments, identity-provider readiness, security findings, threat indicators, vulnerability findings, compliance controls, data policies, service incidents, and recovery plans.
- Sensitive values are removed recursively before persistence. These records do not grant access or silently change identity-provider configuration.

## Wave 10 — Marketplace, revenue and ecosystem expansion (91–100)
- Persistent records for marketplace extensions, extension reviews, entitlements, billing ledger entries, partners, onboarding, attribution, customer health, export requests, and certification reviews.
- Extensions, identity providers, release plans and selected governance records require approval before activation.
- Entitlements and billing entries are ledger metadata only. No payment capture or paid service activation is implemented.

## API reference
All endpoints below require the platform gateway bearer token.
- GET /platform/v1/waves/6-10 — wave and batch catalogue.
- GET /platform/v1/agents and POST /platform/v1/agents — agent registry.
- POST /platform/v1/agent-jobs — create a structured agent job.
- POST /platform/v1/agent-jobs/{job_id}/decision — approve or reject.
- POST /platform/v1/agent-jobs/{job_id}/dispatch — dispatch an approved job to the leased worker queue.
- GET /platform/v1/agent-jobs and GET /platform/v1/agent-jobs/{job_id} — inspect job and linked worker status.
- GET /platform/v1/wave-resources/catalog — all fifty typed resource collections and required fields.
- POST /platform/v1/wave-resources/{resource_type} — create a validated resource.
- GET /platform/v1/wave-resources/{resource_type} and GET /platform/v1/wave-resources/{resource_type}/{resource_id} — read resources.
- PATCH /platform/v1/wave-resources/{resource_type}/{resource_id}/state — governed lifecycle transitions.
- GET /platform/v1/environment/readiness — configuration presence only, never secret values.

## Resource type catalogue
Agent profiles; source reviews; repository snapshots; change proposals; build requests; test runs; documentation reviews; agent delegations; agent knowledge; agent evaluations; software development kit releases; application projects; website projects; workflow definitions; interface components; integrations; application programming interface versions; developer workspaces; dependency reviews; release plans; operating system services; device enrollments; local models; model routes; accessibility profiles; file indexes; system diagnostics; network profiles; backup manifests; privacy consents; organizations; role assignments; identity providers; security findings; threat indicators; vulnerability findings; compliance controls; data policies; service incidents; recovery plans; marketplace extensions; extension reviews; entitlements; billing entries; partners; onboarding records; attribution events; customer health; export requests; certification reviews.

## Security and operational boundaries
- Gateway authentication is required for all Wave 6–10 API routes.
- Worker dispatch is only possible after explicit approval and uses the existing worker authentication, capability check, lease and retry system.
- Agent job types are allowlisted; arbitrary shell and code execution, device unlocking, firmware writes, security bypass, payment capture and secret export are denied.
- Sensitive fields are recursively redacted from resource data.
- Device enrollment requires owner confirmation.
- Local model runtime records must be local.
- Zero-dollar default remains in effect. Payment capture and paid cloud execution are not enabled.
- This repository's gateway currently uses one shared gateway token, not individual Chairman or tenant identities. The records are not represented as multi-tenant isolation until user identity and tenant scoping are implemented.

## Verification
Python continuous integration runs the complete test suite on Python 3.11 and 3.12. Android debug assembly is checked in a separate Java 17 / Gradle 8.9 workflow. A green workflow verifies compilation and tests only; it does not replace device testing, signing, production deployment, or security review.
