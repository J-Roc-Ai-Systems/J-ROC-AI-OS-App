# Platform Core

Wave Two local-first service foundation. The FastAPI router is mounted by the Environment Agent at `/platform/v1`.

The API uses the existing gateway token and must remain behind HTTPS and trusted network controls. This is a single-gateway administrative boundary, not a substitute for per-user identity or tenant-level authorization.

SQLite data defaults to `data/jrocai-platform.sqlite3`; override with `JROCAI_PLATFORM_DATABASE`. Project workspaces default to `workspace/projects`; override with `JROCAI_PROJECT_ROOT`.

## Database migrations

The platform initializes its base schema and applies numbered additive migrations recorded in `schema_migrations`. Migration version 1 adds worker credential hashes, heartbeat timestamps, job lease expiry, bounded retry counts, and cancellation state. Existing databases are upgraded on connection without deleting existing records. Back up the SQLite database before deploying schema changes.

## Worker security and lifecycle

- Worker registration is an authenticated administrative action.
- Registration returns a random per-worker credential once. Store it in the Environment Agent secret manager; do not put it in the Android application or source control.
- Worker list and detail responses never return credential hashes.
- Claim, heartbeat, and finish operations require the worker credential in `X-Worker-Token` as well as the gateway authorization boundary.
- Claims create bounded leases (15–600 seconds). Heartbeats renew active leases.
- Expired leases return jobs to the queue until their configured maximum attempt count is reached.
- Jobs can be cancelled and failed/cancelled jobs can be retried only while retry allowance remains.
- Worker payloads are still data, not executable commands. Workers must use allowlisted handlers and isolated execution environments.

## Routes added in Wave Two hardening

- `POST /platform/v1/workers/{worker_id}/claim` — requires worker credential and lease duration.
- `POST /platform/v1/workers/{worker_id}/heartbeat` — renews active leases.
- `POST /platform/v1/jobs/{job_id}/cancel` — administrative cancellation.
- `POST /platform/v1/jobs/{job_id}/retry` — bounded retry.
- `POST /platform/v1/jobs/recover-expired` — recover expired worker leases.
- `GET /platform/v1/status` — includes applied database migration versions.
- `GET /v1/environment/status` — authenticated secret inventory; returns variable names and configured booleans only, never values.

## Remaining production boundary

The current shared gateway token is not multi-user authentication. Before public exposure, implement per-user identity, tenant authorization, quotas, rate limiting, and audited ownership. No job payload is executed by the API. Device registration does not grant device control. Paid provider calls remain blocked unless both the explicit enable flag and positive monthly spending limit are set.
