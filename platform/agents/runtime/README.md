# J-ROC AI Platform Agent Runtime

**Service identifier:** `jrocai.platform.agent-runtime`  
**Version:** `1.0.0`  
**Host:** Node.js 20 or newer  
**Runtime dependencies:** Node.js built-ins only

## Runtime components

- `agent-registry.mjs`: loads the canonical catalog, validates manifests, and exposes capability and host discovery.
- `policy-engine.mjs`: deny-by-default identity, tenant, host, capability, and single-use approval checks.
- `agent-runtime.mjs`: version-checked dispatch, dependency health checks, execution deadlines, atomic idempotency, safe output redaction, and audit-required fail-closed behavior.
- `http-gateway.mjs`: authenticated discovery and execution endpoints for platform clients.
- `platform-service.mjs`: composes PostgreSQL stores, registry, runtime, HTTP gateway, and durable worker.
- `task-worker.mjs`: claim, execute, complete, requeue, and recover durable tasks with worker leases.
- `environment-agent.mjs`: scoped runtime credential broker. Secret values are exposed only inside an injected adapter callback; raw credentials in adapter results are blocked.
- `source-agent.mjs`: reusable Source Agent orchestration with catalog and inspector adapters.
- `postgres-adapters.mjs`: persistent agent definitions, append-only audit, request-bound approvals, atomic idempotency, and task queue adapters.
- `file-audit-store.mjs`: redacted JSON Lines adapter for local development only.
- `memory-idempotency-store.mjs`: process-local adapter for isolated tests only.

## Run verification

From this directory:

```sh
npm test
npm run check
```

No third-party package installation is required.

## Compose the platform service

The host service supplies:
- A PostgreSQL-compatible database connection pool.
- The canonical catalog file path and platform manifest paths.
- Capability handlers only for agents actually implemented.
- Trusted authentication and host-resolution functions.
- A dependency-health adapter.
- A trusted task-context resolver for background jobs.
- Source catalog and inspection adapters before enabling the Source Agent.

The service returns the shared registry, runtime, HTTP server, worker, and storage adapters. The caller owns process lifecycle and must close its database pool during shutdown. External exposure requires trusted TLS termination, rate limiting, request tracing, and server-side identity.

## HTTP gateway

- `GET /health`: process liveness only.
- `GET /v1/agents`: only agents in the `available` state for the authenticated host.
- `POST /v1/execute`: capability dispatch after identity, tenant, host, permission, approval, dependency, version, and audit checks.

The gateway factory requires injected `authenticate` and `resolveHost` functions. Caller-supplied identity or host headers are not trusted.

## Durable worker

`AgentTaskWorker.processOne()` claims and executes one job. `AgentTaskWorker.run({ signal })` operates a polling loop and exits on shutdown cancellation. The worker must rehydrate and verify the original principal through `resolveExecutionContext`; stored job payloads cannot establish their own authority.

The database uses leases and row-level locking so multiple workers can claim separate jobs. Expired final-attempt jobs are marked failed rather than remaining stuck forever.

## Environment Agent

Agents request secret references, never raw credential values in manifests or prompts. The Environment Agent checks tenant identity and the caller's allowed references, then invokes a trusted adapter callback using short-lived credentials from an injected provider. It audits only reference identifiers and scope metadata, blocks raw credential material in adapter results, and does not return the secret map to the caller.

The real credential provider must be connected to the approved secret manager through the Environment Agent. No credential store, cloud account, provider key, or signing key is bundled in this source.

## Agent lifecycle gate

An entry in the 41-role catalog is a specification, not a running agent. A registered agent is dispatched only when its exact manifest version is loaded and marked `available`, readiness and test states are `passed`, its capability is explicitly declared, the authenticated caller has that capability, the host is supported, dependencies are healthy, a handler is installed, and audit storage is writable.

The Source Agent manifest is registered but is not marked available. It still needs the live source catalog, inspector, persistent stores, and verified deployment wiring.

## Production storage

Apply `../storage/postgres/001_platform_agent_runtime.sql` using the trusted migration role. The migration creates platform definitions, append-only audit events, human approvals, atomic idempotency reservations, and leased task jobs. It enables row-level security, revokes client-role access, and grants backend-only access.

The PostgreSQL adapters expect a connection exposing `query(sql, parameters)` and must be created with a server-side database credential supplied through the Environment Agent. Do not place privileged database credentials in Android, browser code, manifests, workflow files, or source control.

The JSON Lines audit store and in-memory idempotency store are local/test adapters, not production multi-instance persistence. Production must use tenant-aware transactional database adapters, restricted service access, backups, retention controls, and monitoring.

## Cost and security boundaries

The runtime package has no paid service dependency and does not provision cloud resources. Keep the zero-dollar spending gate in force. Agents never store provider credentials, never execute untrusted code during source discovery, and must fail closed when identity, policy, approval, dependency health, or audit storage cannot be verified.
