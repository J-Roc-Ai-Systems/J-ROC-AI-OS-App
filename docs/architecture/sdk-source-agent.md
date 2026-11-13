# J-ROC AI SDK and Source Agent Foundation

## Android SDK
Gradle module: `:sdk:android`
Namespace: `online.jrocai.sdk`
Minimum Android version: API 26
Compile SDK: API 35
Language target: Java 17 / Kotlin 2.0.21

The module exposes `JrocAiSdk`, `AccessTokenProvider`, `SdkCallback`, `SdkResult`, and `AgentTask`. Network calls are asynchronous and use Android's built-in HTTP and JSON APIs. The host application supplies an access token at call time. Never put OpenAI or other model-provider credentials in the Android application.

## Source Agent
The Source Agent is a platform-wide Python service with SQLite persistence. It can be hosted independently of Android and can serve other J-ROC AI clients through the same API contract.

The initial local foundation uses a server-side bearer token from `JROC_SOURCE_AGENT_TOKEN`. This is a bootstrap authentication mode, not a multi-user identity system. Before production, replace or wrap it with the J-ROC AI identity gateway so user and agent scopes are validated individually.

## Agent boundaries
Registered agents: Source Agent, Android Engineering Agent, Environment and Secrets Agent, Quality and Test Agent, Security Agent, and Documentation Agent.

Read-only inspection and proposals can be queued. Source writes, build execution, release publishing, and dependency installation enter `pending_approval`. This foundation records approval and audit history but does not execute arbitrary shell commands or perform Git writes automatically.

## Build and test
Android: `./gradlew :app:assembleDebug` (Windows: `gradlew.bat :app:assembleDebug`).
Python: `python -m unittest discover -s tests/source_agent -v`.
