# J-ROC AI Agent Reusables

Reusable templates and implementation guidance shared by all platform agents.

- `agent-manifest.template.json`: agent identity, capability, permission, dependency, secret, audit, approval, and readiness structure.
- `agent-handler.template.mjs`: bounded handler pattern with cancellation support.
- `AGENT_IMPLEMENTATION_CHECKLIST.md`: lifecycle and verification gates.

Keep shared agent logic in the platform service. Host-specific adapters belong in the respective application; do not fork the canonical registry.
