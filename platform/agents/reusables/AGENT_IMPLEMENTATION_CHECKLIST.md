# Agent Implementation and Activation Checklist

- [ ] Stable identity exists in the canonical catalog.
- [ ] Versioned host-neutral manifest is complete.
- [ ] Each capability has a scope, risk, and explicit permission grant.
- [ ] Supported hosts have real adapters.
- [ ] Dependencies are declared and healthy before dispatch.
- [ ] Secrets are requested through Environment Agent references.
- [ ] Tenant and caller identity are checked on every invocation.
- [ ] High-impact operations require request-bound human approval.
- [ ] Audit events are redacted and durably stored.
- [ ] Handler validates inputs, bounds outputs, and honors cancellation.
- [ ] Untrusted documents and source code are never executed as instructions.
- [ ] Unit, contract, permission, failure, and regression tests pass.
- [ ] Health and readiness checks pass in the target environment.
- [ ] Owner approves the transition to `available`.
- [ ] Rollback and recovery behavior are documented where required.
