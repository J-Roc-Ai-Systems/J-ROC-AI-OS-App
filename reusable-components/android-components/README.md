# Android Reusable Components

Reusable Android components belong here when they can be shared without coupling to a specific screen.

- Use Kotlin and Jetpack Compose.
- Keep network calls out of composable rendering functions.
- Use the Environment Agent as the server-side secret boundary.
- Store account and gateway session tokens through Android Keystore-backed settings.
- Require HTTPS for remote endpoints.
- Represent loading, success, empty, offline and error states explicitly.
- Do not ship provider keys, signing keys, or integration secrets in the package.
- Add accessibility labels and preserve keyboard/screen-reader behavior.
