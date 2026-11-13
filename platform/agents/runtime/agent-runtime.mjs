import { createHash } from "node:crypto";
import { AgentRuntimeError } from "./errors.mjs";
import { PolicyEngine } from "./policy-engine.mjs";

function digest(value) {
  return createHash("sha256").update(JSON.stringify(value)).digest("hex");
}

function sanitizeOutput(value) {
  const secretField = /(password|secret|token|authorization|cookie|private.?key|api.?key)/i;
  if (Array.isArray(value)) return value.map(sanitizeOutput);
  if (!value || typeof value !== "object") return value;
  const safe = {};
  for (const [key, child] of Object.entries(value)) {
    safe[key] = secretField.test(key) ? "[REDACTED]" : sanitizeOutput(child);
  }
  return safe;
}

function validateRequest(request) {
  if (!request || typeof request !== "object") {
    throw new AgentRuntimeError("INVALID_INPUT", "A JSON agent request is required.", 400);
  }
  for (const key of ["requestId", "idempotencyKey", "agentId", "agentVersion", "capability", "tenantId"]) {
    if (typeof request[key] !== "string" || !request[key].trim()) {
      throw new AgentRuntimeError("INVALID_INPUT", `The request field '${key}' is required.`, 400);
    }
  }
  if (!request.requestedBy?.principalId || !request.input || typeof request.input !== "object" || Array.isArray(request.input)) {
    throw new AgentRuntimeError("INVALID_INPUT", "Requesting identity and an object input are required.", 400);
  }
}

export class AgentRuntime {
  constructor({
    registry,
    handlers,
    auditStore,
    approvalStore = null,
    idempotencyStore,
    dependencyHealth = { isHealthy: async () => false },
    policyEngine = new PolicyEngine({ approvalStore }),
    defaultTimeoutMilliseconds = 30000
  }) {
    const hasLegacyIdempotency = idempotencyStore?.get && idempotencyStore?.set;
    const hasAtomicIdempotency = idempotencyStore?.begin && idempotencyStore?.complete;
    if (!registry || !handlers || !auditStore?.append || (!hasLegacyIdempotency && !hasAtomicIdempotency)) {
      throw new TypeError("Registry, handlers, audit store, and a supported idempotency store are required.");
    }
    this.registry = registry;
    this.handlers = handlers;
    this.auditStore = auditStore;
    this.idempotencyStore = idempotencyStore;
    this.dependencyHealth = dependencyHealth;
    this.policyEngine = policyEngine;
    this.defaultTimeoutMilliseconds = defaultTimeoutMilliseconds;
  }

  async #audit(event) {
    try {
      return await this.auditStore.append(event);
    } catch {
      throw new AgentRuntimeError("AUDIT_UNAVAILABLE", "The audit service is unavailable; the agent action was blocked.", 503);
    }
  }

  async execute({ request, principal, host }) {
    validateRequest(request);
    const fingerprint = digest({
      agentId: request.agentId,
      agentVersion: request.agentVersion,
      capability: request.capability,
      tenantId: request.tenantId,
      requestedBy: request.requestedBy,
      input: request.input
    });
    const idempotencyKey = `${request.tenantId}:${request.idempotencyKey}`;
    let ownsReservation = false;

    if (typeof this.idempotencyStore.begin === "function") {
      const claim = await this.idempotencyStore.begin({
        tenantId: request.tenantId,
        idempotencyKey: request.idempotencyKey,
        fingerprint
      });
      if (claim.state === "completed") return claim.response;
      if (claim.state === "conflict") {
        throw new AgentRuntimeError("IDEMPOTENCY_CONFLICT", "This idempotency key was already used for a different request.", 409);
      }
      if (claim.state === "in_progress") {
        throw new AgentRuntimeError("REQUEST_IN_PROGRESS", "An identical request is already executing.", 409);
      }
      if (claim.state !== "acquired") {
        throw new AgentRuntimeError("IDEMPOTENCY_UNAVAILABLE", "The idempotency store returned an invalid reservation state.", 503);
      }
      ownsReservation = true;
    } else {
      const prior = await this.idempotencyStore.get(idempotencyKey);
      if (prior) {
        if (prior.fingerprint !== fingerprint) {
          throw new AgentRuntimeError("IDEMPOTENCY_CONFLICT", "This idempotency key was already used for a different request.", 409);
        }
        return prior.response;
      }
    }

    try {
      return await this.#executeNew({ request, principal, host }, { fingerprint, idempotencyKey, ownsReservation });
    } catch (error) {
      if (ownsReservation && this.idempotencyStore.fail) {
        try {
          await this.idempotencyStore.fail({
            tenantId: request.tenantId,
            idempotencyKey: request.idempotencyKey,
            fingerprint,
            errorCode: error instanceof AgentRuntimeError ? error.code : "AGENT_EXECUTION_FAILED"
          });
        } catch {
          // The database lease will expire and permit recovery after a process failure.
        }
      }
      throw error;
    }
  }

  async #executeNew({ request, principal, host }, reservation) {
    const manifest = this.registry.getAgent(request.agentId);
    if (!manifest) {
      await this.#audit({ event: "agent.dispatch.denied", requestId: request.requestId, agentId: request.agentId, reason: "AGENT_NOT_FOUND" });
      throw new AgentRuntimeError("AGENT_NOT_FOUND", "The requested agent is not registered.", 404);
    }
    if (manifest.lifecycleState !== "available" || !manifest.manifestLoaded) {
      await this.#audit({ event: "agent.dispatch.denied", requestId: request.requestId, agentId: request.agentId, reason: "AGENT_NOT_AVAILABLE" });
      throw new AgentRuntimeError("AGENT_NOT_AVAILABLE", "The agent is registered but is not enabled for execution.", 409);
    }
    if (manifest.version !== request.agentVersion) {
      await this.#audit({ event: "agent.dispatch.denied", requestId: request.requestId, agentId: request.agentId, reason: "VERSION_MISMATCH" });
      throw new AgentRuntimeError("AGENT_VERSION_MISMATCH", "The requested agent version does not match the registered version.", 409);
    }

    let authorization;
    try {
      authorization = await this.policyEngine.authorize({ manifest, request, principal, host });
    } catch (error) {
      await this.#audit({
        event: "agent.execution.denied",
        requestId: request.requestId,
        agentId: manifest.agentId,
        tenantId: request.tenantId,
        principalId: principal?.principalId ?? null,
        capability: request.capability,
        errorCode: error instanceof AgentRuntimeError ? error.code : "PERMISSION_DENIED"
      });
      throw error;
    }
    for (const dependencyId of (manifest.dependencies?.agents ?? [])) {
      const normalizedId = dependencyId.startsWith("jrocai.") ? dependencyId : `jrocai.${dependencyId}`;
      const dependency = this.registry.getAgent(normalizedId);
      if (!dependency || dependency.lifecycleState !== "available" ||
          !(await this.dependencyHealth.isHealthy(normalizedId))) {
        await this.#audit({ event: "agent.dispatch.blocked", requestId: request.requestId, agentId: request.agentId, reason: "DEPENDENCY_UNAVAILABLE" });
        throw new AgentRuntimeError("DEPENDENCY_UNAVAILABLE", "A required agent dependency is not healthy and available.", 503);
      }
    }

    const handlerKey = `${request.agentId}:${request.capability}`;
    const handler = this.handlers instanceof Map ? this.handlers.get(handlerKey) : this.handlers[handlerKey];
    if (typeof handler !== "function") {
      await this.#audit({ event: "agent.dispatch.blocked", requestId: request.requestId, agentId: request.agentId, reason: "HANDLER_NOT_CONFIGURED" });
      throw new AgentRuntimeError("AGENT_NOT_AVAILABLE", "No execution handler is configured for this capability.", 503);
    }

    const startedAt = new Date().toISOString();
    const startedAuditId = await this.#audit({
      event: "agent.execution.started",
      requestId: request.requestId,
      agentId: manifest.agentId,
      agentVersion: manifest.version,
      tenantId: request.tenantId,
      principalId: principal.principalId,
      capability: request.capability,
      approvalId: authorization.approvalId,
      host,
      startedAt
    });

    const requestedTimeout = Number(manifest.execution?.timeoutSeconds ?? 60) * 1000;
    const timeoutMilliseconds = Math.min(
      Math.max(1, requestedTimeout),
      this.defaultTimeoutMilliseconds
    );
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(new Error("Agent execution timed out.")), timeoutMilliseconds);
    try {
      const output = await handler(request.input, Object.freeze({
        signal: controller.signal,
        requestId: request.requestId,
        tenantId: request.tenantId,
        principalId: principal.principalId,
        host,
        agentId: manifest.agentId,
        agentVersion: manifest.version
      }));
      if (controller.signal.aborted) {
        throw new AgentRuntimeError("TIMEOUT", "Agent execution exceeded its time limit.", 504);
      }
      const finishedAt = new Date().toISOString();
      const auditEventId = await this.#audit({
        event: "agent.execution.completed",
        requestId: request.requestId,
        agentId: manifest.agentId,
        tenantId: request.tenantId,
        capability: request.capability,
        startedAuditId,
        finishedAt,
        resultStatus: "completed"
      });
      const response = Object.freeze({
        requestId: request.requestId,
        agentId: manifest.agentId,
        agentVersion: manifest.version,
        status: "completed",
        output: sanitizeOutput(output ?? {}),
        evidence: [],
        auditEventId,
        errors: []
      });
      if (reservation.ownsReservation) {
        await this.idempotencyStore.complete({
          tenantId: request.tenantId,
          idempotencyKey: request.idempotencyKey,
          fingerprint: reservation.fingerprint,
          response
        });
      } else {
        await this.idempotencyStore.set(reservation.idempotencyKey, { fingerprint: reservation.fingerprint, response });
      }
      return response;
    } catch (error) {
      const code = error instanceof AgentRuntimeError ? error.code : (controller.signal.aborted ? "TIMEOUT" : "AGENT_EXECUTION_FAILED");
      const statusCode = error instanceof AgentRuntimeError ? error.statusCode : (controller.signal.aborted ? 504 : 500);
      await this.#audit({
        event: "agent.execution.failed",
        requestId: request.requestId,
        agentId: manifest.agentId,
        tenantId: request.tenantId,
        capability: request.capability,
        startedAuditId,
        errorCode: code,
        resultStatus: "failed"
      });
      throw new AgentRuntimeError(code, "The agent execution failed or could not be verified.", statusCode);
    } finally {
      clearTimeout(timeout);
    }
  }
}
