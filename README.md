# J-ROC AI Android Phone

First-party Android application codebase for the J-ROC AI phone experience.

## Built application areas (0.2.0)

1. **Phone Command Center** — home dashboard and navigation to every module.
2. **J-ROC AI Assistant** — chat UI routed through the J-ROC AI Env Agent.
3. **J-Bot** — device troubleshooting assistant with safety-oriented repair guidance.
4. **Model Center** — Env Agent connection settings, model catalog loading, and model selection.
5. **Conversation Manager** — locally persisted chat history with clear-history control.
6. **Device Tools** — read-only Android hardware, build, and OS diagnostics.
7. **J-ROC AI Account** — account registration and sign-in with an encrypted local session token.
8. **J-ROC AI Settings** — local privacy, gateway-token removal, and history controls.
9. **Ten-Wave Platform Hub** — live Environment Agent service-registry connection and the 100-batch roadmap.

## Security architecture: Env Agent

**Provider secrets do not belong in the Android application or APK.**

- `OPENAI_API_KEY` is configured only in the backend host's encrypted environment/secrets manager.
- `JROCAI_GATEWAY_TOKEN` is a separate gateway credential, not the OpenAI API key.
- The phone stores only its gateway access token encrypted with Android Keystore.
- The phone sends requests to the J-ROC AI Env Agent over HTTPS. The Env Agent calls the OpenAI API server-to-server.
- Real `.env` files, signing keys, keystores, and local configuration are excluded by `.gitignore`.
- Do not paste credentials into GitHub, source code, build logs, screenshots, or chat messages.

The shared gateway-token mechanism remains the administrator API gate. Account sessions are separate and stored encrypted with Android Keystore. Account registration is currently a development foundation: email verification, account recovery, rate limiting, tenant enforcement and Chairman role provisioning remain required before public release.

## Env Agent setup

See [backend/env-agent/README.md](backend/env-agent/README.md).

The backend expects these environment variables, set in the hosting platform's secret manager:

- `OPENAI_API_KEY` — provider credential.
- `JROCAI_GATEWAY_TOKEN` — separate private gateway access token.

A template with placeholder values is provided at `backend/env-agent/.env.example`. It is safe to commit because it contains no real secrets.

## Android requirements

- Android Studio
- JDK 17
- Android SDK Platform 35
- Android Gradle Plugin 8.7.3
- Kotlin 2.0.21

## Build the Android app

Open the repository in Android Studio, sync Gradle, then run the `app` configuration on an Android device or emulator.

Windows command line (if the Gradle wrapper is present):

```powershell
.\gradlew.bat :app:assembleDebug
```

The app requires an HTTPS Env Agent endpoint for live AI calls. Device diagnostics and locally saved conversations can be used without the AI gateway.

## Current implementation boundaries

- ChatGPT-powered assistant and J-Bot calls are wired to the Env Agent API contract; a deployed and configured Env Agent is required for live replies.
- Model Center fetches the model catalog from the Env Agent.
- Conversation history is local to this Android installation; account login and cross-device sync are not implemented.
- Device Tools are read-only device/build diagnostics, not low-level repair or unlock tools.
- The Android Studio IDE plugin is maintained as a separate project/branch.

## Version

Android app: 0.2.0


## Ten-wave build register

See [WAVE_BUILD_PLAN.md](WAVE_BUILD_PLAN.md) for the ten-wave, 100-batch implementation register and honest completion criteria. The current backend includes foundations for account identity, local model routing, repair diagnostics, workflow state, approval-gated build jobs, encrypted user files, enterprise fleet registries and release approvals. These foundations are not a claim that every wave is complete or production-ready.
