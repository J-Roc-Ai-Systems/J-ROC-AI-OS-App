# J-ROC AI Platform Agent Runtime

**Service identifier:** `jrocai.platform.agent-runtime`  
**Version:** `1.0.0`  
**Host:** Node.js 20 or newer  
**Dependencies:** Node.js built-ins only

## Implemented runtime components

- `agent-registry.mjs`: loads the canonical catalog, validates manifests, and exposes capability and host discovery.
- `policy-engine.mjs`: deny-by-default identity, tenant, host, capability, and single-use approval checks.
- `agent-runtime.mjs`: version-checked dispatch, dependency health checks, idempotency, execution timeout, and audited outcomes.
- `http-gateway.mjs`: authenticated agent discovery and execution endpoints for Android, Windows, Linux, web, and cloud host adapters.
- `file-audit-store.mjs`: redacted append-only JSON Lines adapter for local development only.
- `source-agent.mjs`: reusable host-neutral Source Agent orchestration with catalog and inspector ports.

## Run checks

From this directory:

```sh
npm test
npm run check
```

No third-party package installation is required.

## Integration contract

Create the registry with the canonical catalog and validated platform manifests. Supply handlers by the key `<agentId>:<capability>`. Inject an authenticated principal with `authenticated`, `principalId`, `tenantId`, and explicit `grantedCapabilities`. The requesting host is resolved by trusted host integration, never accepted from an untrusted request body.

The runtime requires adapters for:
- persistent idempotency records;
- single-use, request-bound human approvals;
- append-only, tenant-aware audit storage;
- dependency health;
- host authentication and host identity;
- each enabled agent's capability handler.

The runtime deliberately does not ship permissive memory or static-token production defaults. Test fakes belong only in test code.

## HTTP endpoints

- `GET /health`: process liveness only.
- `GET /v1/agents`: returns agents in the `available` state for the authenticated host.
- `POST /v1/execute`: validates identity and policy, then dispatches one capability.

The gateway factory requires injected `authenticate` and `resolveHost` functions. Bind to `127.0.0.1` by default. External deployment must use trusted TLS termination, rate limiting, request tracing, host authentication, and a server-side identity provider. Never trust client-supplied principal or host headers.

## Agent activation gate

An entry in the 41-role catalog is a specification, not a running agent. A manifest can be registered, but dispatch occurs only when its lifecycle state is `available`, its exact version is loaded, its capability is explicitly granted to both the agent and caller, its host is supported, all dependencies are healthy, an execution handler exists, and audit storage is writable.

The Source Agent manifest is registered but intentionally not marked available. It becomes available only after the real source catalog, inspector, persistent audit and idempotency adapters, platform handler registration, and tests are connected.

## Production storage requirements

`JsonLinesAuditStore` is for local development and single-process diagnostics. It is not a multi-instance production audit database and does not make filesystem records tamper-proof. Production must inject a transactional tenant-aware database adapter with restricted append-only permissions, retention controls, backup, and monitoring. The same production requirement applies to approvals and idempotency. Do not silently fall back to memory or local files in production.

## Secrets and cost controls

Agents never store provider credentials. Secret references are resolved through the Environment Agent and short-lived scoped credentials are passed only to the specific adapter that needs them. Secret material must never enter agent inputs, outputs, audit records, mobile packages, or repository files.

The runtime itself has no paid service dependency and does not provision cloud resources. The platform zero-dollar spending gate remains in force.
