# J-ROC AI Reusable Components

This directory is the shared library for reusable application, backend, agent, worker, workflow, integration, security, database, and documentation components.

## Rules
- Inspect existing components before recreating or replacing them.
- Keep templates free of real credentials, private keys, customer data, and production database files.
- Put secret names and references in templates; resolve values only through the Environment Agent.
- Record supported versions, required permissions, ownership, and integration points.
- Generated code is reviewed before execution or release.

## Categories
- `application-templates/` — application and project scaffolds.
- `agent-templates/` — agent capability and permission contracts.
- `worker-templates/` — worker enrollment and execution contracts.
- `workflow-templates/` — versioned workflow definitions.
- `integration-templates/` — secret-reference-only integration contracts.
- `security-templates/` — deny-by-default security contracts.
- `database-migrations/` — migration authoring and upgrade rules.
- `android-components/` — reusable Jetpack Compose and Android guidance.
- `build-templates/` — approval-gated build recipes.
- `observability-templates/` — safe audit and telemetry conventions.
- `documentation-templates/` — reusable operator and developer documentation.
