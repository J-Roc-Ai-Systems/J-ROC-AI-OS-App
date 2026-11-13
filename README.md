# J-ROC AI Android App

First-party Android application codebase for the J-ROC AI phone experience.

## Project principles
- Native Android application built with Kotlin and Jetpack Compose.
- Local-first architecture; cloud services are optional integrations.
- API credentials must never be committed to source control or embedded in the APK.
- No paid third-party dependency is required to compile the starter application.
- Keep product modules separated so the phone interface, assistant, tools, and settings can evolve independently.

## Requirements
- Android Studio (current stable release)
- JDK 17
- Android SDK Platform 35
- Android Gradle Plugin 8.7.3
- Kotlin 2.0.21

## Build
Open this repository in Android Studio, allow Gradle sync, then run the `app` configuration on an Android device or emulator.

Command line (Windows):
```powershell
.\gradlew.bat :app:assembleDebug
```

## Initial application structure
- `app/src/main/java/online/jrocai/phone/MainActivity.kt` — Compose application shell and home dashboard.
- `app/src/main/AndroidManifest.xml` — Android application declaration.
- Future modules: assistant runtime, model routing, device tools, conversations, settings, and account sync.

## Secrets and API configuration
Do not place OpenAI or other provider keys in Kotlin files, Gradle files, assets, or GitHub. For production, route provider requests through an authenticated backend. For local development, use an untracked local configuration file or Android Studio run configuration and keep it out of commits.

## Status
Foundation commit: native Android shell and build configuration. This is a starting codebase, not a claim that all phone OS features or AI integrations are already implemented.
