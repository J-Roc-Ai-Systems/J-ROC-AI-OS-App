# J-ROC AI Final Validation Plan

**Execution rule:** Do not run this validation until implementation across all ten waves is complete and the owner requests the final validation phase. This file is a test specification, not evidence of passing tests.

## 1. Source and configuration checks
- Confirm the intended repository, branch and commit.
- Confirm existing Android entry point, routes, branding, and local conversation persistence remain present.
- Confirm all server credentials are Environment Agent references or protected environment variables.
- Scan tracked files, build outputs and logs for real keys, passwords, tokens, signing material and private customer data.
- Confirm the strict zero-dollar cloud gate defaults to disabled and a zero monthly limit.
- Confirm remote Android connections require HTTPS and local model URLs are loopback-only.

## 2. Database and migration checks
- Migrate a new empty database through every ordered migration.
- Upgrade a copy of each supported prior database without losing user, worker, job, conversation or project records.
- Re-run migrations and confirm idempotency.
- Interrupt a migration in a disposable database and verify rollback/retry behavior.
- Verify foreign keys, indexes, uniqueness constraints and migration history.
- Back up and restore a database copy; verify row counts and referential integrity.

## 3. Identity and security checks
- Register a member account and verify password hashing and one-time session token issuance.
- Verify no plaintext password or session token is persisted.
- Verify session expiry, logout revocation and invalid-token rejection.
- Verify repeated failed login lockout and successful login reset behavior.
- Verify Chairman role assignment is denied unless the protected Environment Agent flag is explicitly enabled.
- Verify gateway administrator token and worker token are not interchangeable.
- Verify a worker cannot claim or finish another worker's job.
- Verify paused and disabled workers cannot claim jobs.
- Verify audit redaction and that secrets never appear in audit rows.
- Verify account file ownership isolation across two users.

## 4. Worker, agent and workflow checks
- Register workers and verify credential rotation and revocation.
- Verify capability matching, maximum concurrency, job claim atomicity and lease expiry recovery.
- Verify heartbeat and lease renewal only work for the authenticated worker and its own active job.
- Verify expired leases return work to the queue.
- Verify agent versions are immutable and only allowlisted permissions are accepted.
- Verify publishing a draft agent supersedes the prior published version.
- Verify workflow step order, valid transitions, terminal-state protection and failure handling.
- Verify worker execution is isolated, network egress is denied by default and untrusted code cannot run in the Env Agent process.

## 5. Local model and cloud-spending checks
- Discover a local Ollama runtime and model catalog.
- Run assistant and J-Bot requests through a local model.
- Verify a missing local model does not trigger cloud inference when the spending gate is disabled.
- Verify a configured provider key alone does not enable cloud inference.
- Verify cloud inference requires both explicit enablement and a positive monthly limit.
- Verify prompt and response content are not written to telemetry or audit logs.
- Verify local model URL rejects remote hosts, credentials and non-loopback destinations.

## 6. Repair and device checks
- Register compatibility profiles and validate approved USB, wireless and local-only methods.
- Verify unsupported methods are rejected.
- Create, update, resolve and close diagnostic sessions.
- Verify unknown device and profile references are rejected.
- Verify destructive repair actions require explicit warning and user confirmation.
- Verify no unsupported unlock, bypass or device-opening claims are presented.

## 7. Build factory and release checks
- Create versioned build recipes and projects.
- Verify a build run begins in pending approval.
- Verify no worker job is queued before approval.
- Verify approval queues only a capability-scoped job and never executes shell commands in the API process.
- Verify worker-reported completion is not confused with independently verified artifact provenance.
- Verify release channels, pending approval, approval records and distribution-ready state transitions.
- Verify release readiness does not claim a deployment occurred.
- Verify package signing keys remain outside Git and Android source.

## 8. Encrypted file storage checks
- Verify upload rejects invalid Base64, empty files and files larger than 5 MiB.
- Verify AES-GCM encryption, authenticated decryption and ciphertext integrity.
- Verify the Environment Agent key is required and malformed keys fail closed.
- Verify user A cannot list, download or delete user B's files.
- Verify path traversal and symbolic-link attacks are rejected.
- Verify key backup and restore procedures before production file retention.

## 9. Enterprise and integration checks
- Verify organization, member, fleet enrollment and policy records.
- Verify duplicate enrollment and invalid member references return safe errors.
- Verify enterprise role enforcement at every protected resource, not just in the interface.
- Verify integration credentials are stored only through Environment Agent secret references.
- Verify fleet operations are audit logged and device authorization is explicit.
- Verify quotas, rate limits, monitoring, backup and recovery before enabling enterprise use.

## 10. Android build and device validation
- Run Gradle configuration and dependency resolution.
- Build the debug package and release package.
- Run unit tests, instrumentation tests and Compose navigation tests.
- Verify account registration, login, saved session check and logout.
- Verify identity and gateway tokens are encrypted using Android Keystore.
- Verify the Platform Hub connects to the Env Agent and displays live service/model/workflow/repair/build/release counts.
- Verify offline, loading, empty, timeout, server error and invalid-token states.
- Verify phone, tablet and supported Android version layouts.
- Verify no provider key or signing secret is present in the package.

## 11. Release acceptance
A wave is accepted only when all ten batches for that wave have implementation, integration, documentation and source-inspection evidence. The platform is not release-ready until every required automated and manual check passes, artifacts are verified, rollback is demonstrated and the owner approves the release candidate.

## Current state
No validation commands, tests, Android builds, APK generation, signing, deployment or release publication have been run in the current implementation phase.
