# Platform Core

Wave Two local-first service foundation. The FastAPI router is mounted by the Env Agent at `/platform/v1`.

The API uses the existing gateway token and must remain behind HTTPS and trusted network controls. This is a single-gateway service boundary, not a substitute for per-user authentication or tenant-level authorization.

SQLite data defaults to `data/jrocai-platform.sqlite3`; override with `JROCAI_PLATFORM_DATABASE`. Project workspaces default to `workspace/projects`; override with `JROCAI_PROJECT_ROOT`.

Worker jobs are durable records. This release does not execute submitted payloads; registered workers poll, claim, and report results. Worker processes must enforce their own allowlisted task handlers and execution sandbox.
