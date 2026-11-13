# J-ROC AI Python Platform SDK

A standard-library client for the shared J-ROC AI platform API. Use HTTPS except for local loopback development. Pass the gateway access token at runtime from the Environment Agent or a protected secret store. Never commit tokens or place them in application source.

The current gateway token is a development boundary, not per-user authentication. Do not expose this SDK to untrusted clients until identity and tenant authorization are implemented.
