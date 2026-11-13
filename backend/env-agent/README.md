# J-ROC AI Env Agent

The Env Agent is the server-side boundary for secrets and provider requests.

## Secret policy

- `OPENAI_API_KEY` exists only in the backend hosting provider's encrypted environment/secrets settings.
- `JROCAI_GATEWAY_TOKEN` is a separate long random gateway access token. It is not the OpenAI key.
- Never commit a real `.env`, print environment values, return secrets from an API, or include provider keys in the Android app, APK, logs, screenshots, or GitHub.
- The Android app stores only the gateway access token encrypted with Android Keystore. For production, replace the shared gateway token with per-user authentication (for example Supabase Auth JWT validation) and rate limits.

## Run locally

Python 3.11+:

```powershell
cd backend/env-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
# Edit .env locally with real values; .env is ignored by Git.
uvicorn app:app --host 127.0.0.1 --port 8787
```

Set all required values in the deployment platform's secret/environment settings for hosted deployments. Use HTTPS for remote connections.

Optional local model settings:
- `JROCAI_LOCAL_MODEL_BASE_URL` — Ollama-compatible local runtime; the adapter accepts loopback HTTP addresses only.
- `JROCAI_FILE_ENCRYPTION_KEY` — Base64URL-encoded 32-byte AES key held only by the Environment Agent secret manager.
- `JROCAI_ENCRYPTED_FILE_ROOT` — local encrypted blob directory.

Never use the example placeholder as an encryption key. Back up the encryption key separately from the encrypted file database; losing the key makes stored files unrecoverable.

## API

- `GET /health` — public service status only; never returns secret values.
- `GET /v1/models` — authenticated model catalog.
- `POST /v1/chat` — authenticated J-ROC AI Assistant or J-Bot request.
- `POST /identity/v1/register`, `POST /identity/v1/login`, `GET /identity/v1/me`, `POST /identity/v1/logout` — account session foundation.
- `GET /platform/v1/local-models/status`, `POST /platform/v1/local-models/chat` — loopback-only local model runtime.
- `/platform/v1/workflows` — versioned workflow definitions and run state.
- `/platform/v1/repair` — compatibility profiles and diagnostic sessions.
- `/platform/v1/builds` — approval-gated build recipes and worker job queue.
- `/identity/v1/files` — per-user encrypted file upload, listing, download and deletion.
- `/platform/v1/enterprise` — organization, membership, fleet and policy registry.
- `/platform/v1/releases` — release channels and approval/distribution state registry.

Account registration currently creates a member account and a 12-hour session. Email verification, account recovery, login rate limits, tenant-level enforcement and Chairman role provisioning are not yet implemented. The build queue does not execute commands in the API process; a separately isolated and authorized worker runtime is still required. A release marked ready for distribution has not been deployed.

The gateway token is checked with constant-time comparison. Provider errors are sanitized before returning to the phone. Account identity is a development foundation only. Add email verification, recovery, login rate limits, tenant authorization and security review before public production deployment.

## Zero-dollar spending gate

Paid cloud model calls are blocked unless both `JROCAI_ALLOW_PAID_CLOUD=true` and `JROCAI_MONTHLY_SPENDING_LIMIT_USD` is greater than zero are explicitly configured in the protected backend environment. The default is disabled with a zero-dollar limit. A provider key being present does not authorize spending. Never place these settings or provider credentials in the Android application package.
