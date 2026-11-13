# J-ROC AI Source Agent

A permanent platform-wide source intelligence and development service, independent of Android. It provides an authenticated agent registry, persistent task queue, approval gates, and audit events for repository inspection, source proposals, builds, tests, dependencies, and documentation.

## Security
- Production must run behind authenticated HTTPS.
- Set `JROC_SOURCE_AGENT_TOKEN` on the server; never commit it.
- Android receives only a short-lived session token from the host app.
- Model-provider credentials stay on the server.
- Source writes, build execution, dependency installation, and releases require explicit approval.
- This foundation queues and gates work; it does not execute arbitrary shell commands or silently modify repositories.

## Run
Python 3.12+, standard library only:
```powershell
$env:JROC_SOURCE_AGENT_TOKEN = "use-a-random-secret-at-least-32-characters"
python -m source_agent
```
Default bind: `127.0.0.1:8788`. Configure host, port, and database with `JROC_SOURCE_AGENT_HOST`, `JROC_SOURCE_AGENT_PORT`, and `JROC_SOURCE_AGENT_DATABASE`.

## API
- `GET /health`
- `GET /v1/agents` (authenticated)
- `POST /v1/tasks` (authenticated)
- `GET /v1/tasks/{task_id}` (authenticated)
- `POST /v1/tasks/{task_id}/approve` (authenticated)

Task states: `queued`, `pending_approval`, and `rejected`.
