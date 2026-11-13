# J-ROC AI Developer Tools for Android Studio

This is a standalone Android Studio IDE plugin project. It is separate from the Android phone application module.

## Included in version 0.1.0

- **J-ROC AI tool window:** project workflow and security guidance.
- **Compose screen starter:** right-click in an editor and select **Insert J-ROC Compose Screen**.
- **Safe credential guidance:** no API key field, key storage, or embedded provider secret is included.

## Build

Requirements:
- JDK 21
- Gradle 9.0 or newer
- Android Studio / IntelliJ Platform compatible with build 251 or newer

From this directory:

```powershell
gradle buildPlugin
```

The distributable ZIP is written under `build/distributions/`.

To run a development IDE instance:

```powershell
gradle runIde
```

The build targets Android Studio 2025.1.1.13 through the IntelliJ Platform Gradle Plugin. Confirm the target platform version against the installed Android Studio build before release.

## Install the ZIP

1. Build the plugin with `gradle buildPlugin`.
2. In Android Studio, open **Settings > Plugins**.
3. Open the gear menu and choose **Install Plugin from Disk**.
4. Select the ZIP from `build/distributions`.
5. Restart Android Studio.
6. Open **View > Tool Windows > J-ROC AI**.

This plugin does not automatically call an AI provider. AI chat, code generation, and remote model routing require a separately implemented authenticated backend integration.
