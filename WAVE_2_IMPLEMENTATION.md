# Wave 2 Implementation Record

Branch: `wave-2-intelligence-production`
Base: `a4d7891139521f7fc55822841ad841dcec4f0287`

## This implementation increment

- Added an ordered SQLite schema migration runner with a persistent `schema_migrations` ledger.
- Added a baseline migration and an additive worker identity and lease migration. Existing installations retain existing records; the migration checks the lease column before adding it.
- Worker registration now rotates a cryptographically random worker credential and returns it once. Only a SHA-256 digest is stored in SQLite; the plaintext credential must be transferred into the Environment Agent secret store.
- Worker job claiming and completion use a separate worker API router, require an individual worker credential, and verify the authenticated worker identity.
- Added worker credential revocation and bounded job leases with stale-job recovery.
- Administrator operations remain behind the Environment Agent gateway token.
- The zero-dollar cloud spending gate remains unchanged.

## Security boundary

The gateway token authorizes platform administration. A worker credential authorizes only that worker's claim and completion endpoints. Worker credentials are hashed at rest and can be revoked. This is not yet multi-user Chairman account identity or a hardened process sandbox. Worker code must run in a separately isolated runtime; the API does not execute arbitrary worker payloads.

## Wave Two delivery checklist

| Requirement | Current status | Evidence |
|---|---|---|
| Ten batch foundations | In progress | Existing modules and Android Wave Two hub retained |
| Platform service registration | Implemented foundation | Existing startup service registration |
| Android hub navigation | Integrated | Existing MainActivity navigation |
| Backend and versioned database migrations | Implemented foundation | Migration ledger and ordered baseline/additive migrations |
| Agent and worker permissions | Implemented foundation | Gateway administration token, individual worker credentials, identity matching, revocation, bounded leases |
| Environment Agent secret management | Implemented boundary | Worker token is one-time returned; integration credentials remain secret references |
| Zero-dollar spending gate | Enforced at provider gateway | Paid cloud requests remain disabled unless both explicit enablement and positive limit are configured |
| Reusable components | Initial contracts documented | reusable-components folder retained |
| Dependencies and configuration | Documented | Existing FastAPI/Pydantic/SQLite and Android dependencies |
| Comprehensive final test plan | Prepared, not executed | Validation deferred until the full build is complete |

**Source inspection status:** the two previously outstanding foundations now have implementation code. This is not a test result. Wave Two remains under development; no build, automated test, security test, APK generation, or deployment was run in this increment.

## Deferred implementation

- Full Chairman account identity and tenant-level authorization.
- Worker process sandboxing, operating-system isolation, network egress policy and signed worker packages.
- Lease renewal/heartbeat and configurable retry/backoff/dead-letter policy.
- Android live data binding, operational sub-screens and explicit loading/error/empty states.
- Live model routing adapters, encrypted file upload/storage and quota enforcement.
- Provider-specific integration approval and device discovery/authorization workflows.
- Application install/update adapters with user approval.

## Final validation plan

After the entire build is complete, run one consolidated validation wave covering migration from an empty database and an existing database, migration idempotency, worker credential issuance/revocation, identity mismatch rejection, lease expiry recovery, concurrency and capability enforcement, API gateway authentication, secret redaction, path safety, Android navigation, backend integration, and full Android debug/release builds.
