# J-ROC AI Reusable Components

This directory is the shared library for reusable application, backend, agent, worker, workflow, integration, security, database, and documentation components.

## Rules
- Inspect existing components before recreating or replacing them.
- Keep templates free of real credentials, private keys, customer data, and production database files.
- Put secret names and references in templates; resolve values only through the Environment Agent.
- Record supported versions, required permissions, ownership, and integration points.
- Generated code is reviewed before execution or release.

## Categories
- `application-templates/`
- `agent-templates/`
- `worker-templates/`
- `workflow-templates/`
- `integration-templates/`
- `security-components/`
- `database-components/`
- `android-components/`
- `documentation-templates/`
