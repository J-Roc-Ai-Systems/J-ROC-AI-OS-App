# Observability Reusables

- Record event identifiers, timestamps, service names and safe status values.
- Never record passwords, session tokens, API keys, private prompts or file contents.
- Redact sensitive values before audit persistence.
- Distinguish service registration from successful health checks.
- Distinguish worker-reported completion from independently verified artifacts.
- Keep metrics local by default; remote telemetry requires explicit approval.
