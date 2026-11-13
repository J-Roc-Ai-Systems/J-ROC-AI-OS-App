import { AgentRuntimeError } from "./errors.mjs";

const SECRET_REFERENCE = /^[a-zA-Z0-9][a-zA-Z0-9._:/-]{0,199}$/;

/**
 * The Environment Agent never returns secret values to agent callers.
 * Secrets are made available only inside an injected adapter callback.
 */
export class EnvironmentAgent {
  constructor({ credentialProvider, auditStore, clock = () => Date.now() }) {
    if (!credentialProvider?.resolve || !auditStore?.append) {
      throw new TypeError("A secret provider and audit store are required.");
    }
    this.credentialProvider = credentialProvider;
    this.auditStore = auditStore;
    this.clock = clock;
  }

  async withCredentials({ references, principal, purpose, tenantId, taskId }, operation) {
    if (!principal?.authenticated || !principal.principalId || !tenantId ||
        principal.tenantId !== tenantId || !purpose || typeof operation !== "function") {
      throw new AgentRuntimeError("PERMISSION_DENIED", "A verified caller, tenant, purpose, and adapter operation are required.", 403);
    }
    if (!Array.isArray(references) || references.length < 1 || references.length > 10 ||
        references.some((reference) => typeof reference !== "string" || !SECRET_REFERENCE.test(reference)) ||
        new Set(references).size !== references.length) {
      throw new AgentRuntimeError("INVALID_INPUT", "One to ten unique valid secret references are required.", 400);
    }
    for (const reference of references) {
      if (!principal.secretReferences?.includes(reference)) {
        await this.auditStore.append({
          event: "environment.secret_access.denied",
          tenantId,
          principalId: principal.principalId,
          secretReference: reference,
          purpose,
          taskId: taskId ?? null
        });
        throw new AgentRuntimeError("PERMISSION_DENIED", "The caller is not authorized for one of the requested secret references.", 403);
      }
    }

    const credentials = Object.create(null);
    const metadata = [];
    try {
      for (const reference of references) {
        const credential = await this.credentialProvider.resolve({
          reference,
          tenantId,
          principalId: principal.principalId,
          purpose
        });
        if (!credential || typeof credential.value !== "string" || !credential.value ||
            !Number.isFinite(credential.expiresAt) || credential.expiresAt <= this.clock()) {
          throw new AgentRuntimeError("CREDENTIAL_UNAVAILABLE", "A scoped credential could not be issued or has expired.", 503);
        }
        credentials[reference] = credential.value;
        metadata.push({ reference, expiresAt: credential.expiresAt, scope: credential.scope ?? null });
      }

      await this.auditStore.append({
        event: "environment.secret_access.granted",
        tenantId,
        principalId: principal.principalId,
        purpose,
        taskId: taskId ?? null,
        references: metadata.map(({ reference, expiresAt, scope }) => ({ reference, expiresAt, scope }))
      });

      // Values are passed only to the trusted adapter callback and never returned.
      return await operation(Object.freeze({ ...credentials }));
    } finally {
      for (const reference of Object.keys(credentials)) credentials[reference] = "";
    }
  }
}
