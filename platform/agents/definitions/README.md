# Platform Agent Definitions

Every specialist agent has its own directory and versioned manifest. The canonical identity and domain come from `../registry/agent-catalog.json`.

## Rules
- A definition is a specification, not an executable implementation.
- All agents start as `specified`; the Source Agent is `registered` because it has a platform contract and an initial implementation foundation.
- No agent becomes `available` until implementation, handlers, dependencies, audit storage, readiness checks, tests, and owner approval are complete.
- Capabilities are declared and permissioned individually.
- External writes, production changes, financial actions, destructive actions, access changes, and private repository access require human approval.
- All credentials are owned by the Environment Agent.
- Untrusted source code is never executed during discovery or indexing.

All agents are host-neutral. Supported-host declarations describe portability goals; they do not claim that every host adapter already exists.
