import { readFile } from "node:fs/promises";
import { AgentRuntimeError } from "./errors.mjs";

const LIFECYCLE_STATES = new Set(["specified", "registered", "available", "degraded", "disabled", "retired"]);

function normalizeCatalogEntry(entry) {
  if (!Array.isArray(entry) || entry.length !== 4) {
    throw new AgentRuntimeError("INVALID_REGISTRY", "Every catalog entry must contain four fields.", 500);
  }
  const [slug, displayName, description, domain] = entry;
  if (![slug, displayName, description, domain].every((value) => typeof value === "string" && value.trim())) {
    throw new AgentRuntimeError("INVALID_REGISTRY", "Catalog entries contain an empty or invalid field.", 500);
  }
  return Object.freeze({
    agentId: `jrocai.${slug}`, slug, displayName, description, domain,
    lifecycleState: "specified", version: null,
    capabilities: Object.freeze([]), supportedHosts: Object.freeze([]), manifestLoaded: false
  });
}

export class AgentRegistry {
  #agents = new Map();

  constructor({ catalog, manifests = [] }) {
    if (!catalog || !Array.isArray(catalog.agents)) {
      throw new AgentRuntimeError("INVALID_REGISTRY", "The platform agent catalog is missing or invalid.", 500);
    }
    for (const entry of catalog.agents) {
      const normalized = normalizeCatalogEntry(entry);
      if (this.#agents.has(normalized.agentId)) {
        throw new AgentRuntimeError("INVALID_REGISTRY", `Duplicate agent identifier: ${normalized.agentId}`, 500);
      }
      this.#agents.set(normalized.agentId, normalized);
    }
    for (const manifest of manifests) this.register(manifest);
  }

  register(manifest) {
    if (!manifest || typeof manifest !== "object") {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Agent manifest must be an object.", 400);
    }
    const current = this.#agents.get(manifest.agentId);
    if (!current) throw new AgentRuntimeError("AGENT_NOT_FOUND", "The agent is not in the platform catalog.", 404);
    if (manifest.scope !== "platform-wide" || !manifest.owner || !manifest.version) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Manifest scope, owner, and version are required.", 400);
    }
    if (!LIFECYCLE_STATES.has(manifest.lifecycleState)) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Manifest lifecycle state is invalid.", 400);
    }
    if (!Array.isArray(manifest.capabilities) || !Array.isArray(manifest.supportedHosts) ||
        manifest.supportedHosts.some((host) => typeof host !== "string" || !host.trim())) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Manifest capabilities and supported hosts must be valid arrays.", 400);
    }
    const capabilityIds = manifest.capabilities.map((capability) =>
      typeof capability === "string" ? capability : capability?.id
    );
    if (capabilityIds.some((id) => typeof id !== "string" || !id.trim()) ||
        new Set(capabilityIds).size !== capabilityIds.length) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Capability identifiers must be unique non-empty strings.", 400);
    }
    const permissionCapabilities = manifest.permissions?.capabilities;
    if (!Array.isArray(permissionCapabilities) ||
        capabilityIds.some((id) => !permissionCapabilities.includes(id))) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Every declared capability must also be explicitly permitted.", 400);
    }
    if (!manifest.audit?.required || manifest.secrets?.environmentAgentManaged !== true) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Audit logging and Environment Agent secret ownership are mandatory.", 400);
    }
    if (manifest.lifecycleState === "available" &&
        (manifest.health?.status !== "passed" || manifest.tests?.status !== "passed")) {
      throw new AgentRuntimeError("AGENT_NOT_AVAILABLE", "An agent cannot become available until readiness checks and capability tests pass.", 409);
    }
    if (manifest.execution?.timeoutSeconds !== undefined &&
        (!Number.isInteger(manifest.execution.timeoutSeconds) || manifest.execution.timeoutSeconds < 1 || manifest.execution.timeoutSeconds > 3600)) {
      throw new AgentRuntimeError("INVALID_MANIFEST", "Execution timeout must be between 1 and 3600 seconds.", 400);
    }
    const registered = Object.freeze({
      ...current, ...manifest,
      capabilities: Object.freeze([...manifest.capabilities]),
      supportedHosts: Object.freeze([...manifest.supportedHosts]),
      manifestLoaded: true
    });
    this.#agents.set(manifest.agentId, registered);
    return registered;
  }

  getAgent(agentId) {
    return this.#agents.get(agentId) ?? null;
  }

  list({ host, availableOnly = false } = {}) {
    return [...this.#agents.values()]
      .filter((agent) => !availableOnly || agent.lifecycleState === "available")
      .filter((agent) => !host || agent.supportedHosts.includes(host))
      .map((agent) => ({
        agentId: agent.agentId, displayName: agent.displayName,
        description: agent.description, domain: agent.domain,
        lifecycleState: agent.lifecycleState, version: agent.version,
        capabilities: agent.capabilities, supportedHosts: agent.supportedHosts
      }));
  }

  get size() {
    return this.#agents.size;
  }
}

export async function loadAgentRegistry({ catalogPath, manifestPaths = [] }) {
  const catalog = JSON.parse(await readFile(catalogPath, "utf8"));
  const manifests = await Promise.all(manifestPaths.map(async (path) =>
    JSON.parse(await readFile(path, "utf8"))
  ));
  return new AgentRegistry({ catalog, manifests });
}
