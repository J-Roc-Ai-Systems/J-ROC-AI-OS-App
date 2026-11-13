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

Set the two values in the deployment platform's secret/environment settings for hosted deployments. Use HTTPS for remote connections.

## API

- `GET /health` — public service status only; never returns secret values.
- `GET /v1/models` — authenticated model catalog.
- `POST /v1/chat` — authenticated J-ROC AI Assistant or J-Bot request.

The gateway token is checked with constant-time comparison. Provider errors are sanitized before returning to the phone. Add user-level identity, quotas, abuse controls, and audit events before public production deployment.

## Zero-dollar spending gate

Paid cloud model calls are blocked unless both `JROCAI_ALLOW_PAID_CLOUD=true` and `JROCAI_MONTHLY_SPENDING_LIMIT_USD` is greater than zero are explicitly configured in the protected backend environment. The default is disabled with a zero-dollar limit. A provider key being present does not authorize spending. Never place these settings or provider credentials in the Android application package.
