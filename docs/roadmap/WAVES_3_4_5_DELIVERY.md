# Wave Three, Four and Five delivery record

**Branch:** `wave-2-intelligence-production`

**Scope:** Batches 21–50, 30 batch definitions across three waves.

## Source changes

- `backend/env-agent/platform_core/wave345.py`: shared service catalogue, durable workflow governance, policy decisions and governance summary.
- `backend/env-agent/app.py`: mounts the Wave Three–Five API router.
- `backend/env-agent/platform_core/WAVES_3_4_5.md`: detailed scope and delivery boundaries.
- `backend/env-agent/platform_core/domain_records.py`: persistent record APIs for all twenty Wave Four and Five domains, with lifecycle validation and credential-field filtering.
- `tests/test_waves_three_to_five.py`: regression coverage for catalogue integrity, approval flow, policy gates and domain records.

## API routes

- `GET /platform/v1/waves`
- `POST /platform/v1/workflows`
- `GET /platform/v1/workflows`
- `GET /platform/v1/workflows/{workflow_id}`
- `POST /platform/v1/workflows/{workflow_id}/decision`
- `POST /platform/v1/workflows/{workflow_id}/cancel`
- `POST /platform/v1/policy/evaluate`
- `GET /platform/v1/policy/decisions`
- `GET /platform/v1/governance/overview`

All routes inherit the platform gateway authentication dependency. Workflow approvals only change persisted workflow state; they do not trigger execution.

## Domain record routes

- `GET /platform/v1/domain/catalog`
- `POST /platform/v1/domain/{domain}/records`
- `GET /platform/v1/domain/{domain}/records`
- `GET /platform/v1/domain/{domain}/records/{record_id}`
- `PATCH /platform/v1/domain/{domain}/records/{record_id}/state`

## Validation

Tests are authored and a GitHub Actions run has been queued; results must be checked before claiming a pass. Android builds, full repository tests and runtime integration remain unverified. Do not describe these waves as production complete. The Wave Four and Wave Five domain-specific adapters remain separate implementation work, even though their batch catalogue and governance entry points are now registered.
