# Reusable Wave Six Through Ten Components

This folder documents shared components intended for reuse across the J-ROC AI phone application, desktop and web clients, platform agents, and backend services.

## Components
- Agent job contract: ../../backend/env-agent/platform_core/wave610.py
- Worker execution contract: backend/env-agent/platform_core/workers.py
- Platform agent registry: backend/env-agent/platform_core/wave610.py
- Shared Android API client: app/src/main/java/online/jrocai/phone/data/WaveSixTenPlatformClient.kt
- Encrypted gateway settings: app/src/main/java/online/jrocai/phone/data/SecureSettings.kt
- Typed resource registry: backend/env-agent/platform_core/wave610.py

## Reuse rules
- Reuse the shared authenticated gateway client; never place provider keys in client applications.
- Keep all remote calls HTTPS-only. Loopback HTTP is permitted only for local development.
- Use typed agent job names from the server allowlist.
- Require explicit approval before dispatching agent jobs.
- Worker implementations must use worker credentials, capability checks, leases, bounded retries, and structured result payloads.
- Persist resource metadata through the shared resource API; redact secrets before persistence.
- Keep paid services disabled by default and use local-first execution.
- Do not implement shell execution, device unlocking, firmware writes, payment capture, or security bypass through these contracts.
