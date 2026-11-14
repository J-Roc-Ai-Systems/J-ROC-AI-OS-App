# Reusable Components — Waves Eleven Through Fifteen

Shared backend service foundations for batches 101–150.

- The authenticated FastAPI router lives in backend/env-agent/platform_core/wave1115.py.
- Collection names, batch numbers, and required fields are defined once in COLLECTIONS and REQUIRED.
- All new service records use the common lifecycle and recursive sensitive-field filtering.
- Use the collection catalogue endpoint rather than duplicating collection metadata in clients.
- Keep external actions behind separately authorized workers and explicit approval.
- Do not store raw credentials, payment instruments, or secret values in records.
- Keep cloud spending disabled by default.

See docs/architecture/WAVES_11_15_PLATFORM_SERVICES.md for the API contract and current limitations.
