import { readFile, readdir } from "node:fs/promises";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { AgentRegistry } from "./agent-registry.mjs";
import { AgentRuntime } from "./agent-runtime.mjs";
import { PolicyEngine } from "./policy-engine.mjs";
import { AgentTaskWorker } from "./task-worker.mjs";
import { createAgentHttpServer, listenAgentHttpServer } from "./http-gateway.mjs";
import { createPostgresAgentStores } from "./postgres-adapters.mjs";
import { createSourceAgentHandlers } from "./source-agent.mjs";

async function discoverAgentManifests(definitionsDirectory) {
  const root = typeof definitionsDirectory === "string"
    ? definitionsDirectory
    : fileURLToPath(definitionsDirectory);
  const entries = await readdir(root, { withFileTypes: true });
  const manifestPaths = entries
    .filter((entry) => entry.isDirectory())
    .map((entry) => join(root, entry.name, "agent-manifest.json"));
  return Promise.all(manifestPaths.map(async (path) =>
    JSON.parse(await readFile(path, "utf8"))
  ));
}

/**
 * Compose the host-neutral service. The caller owns the PostgreSQL connection
 * pool and must provide trusted authentication, host resolution, dependency
 * health, and single-use human approval integration.
 */
export async function createPlatformAgentService({
  catalogPath,
  definitionsDirectory = new URL("../definitions/", import.meta.url),
  manifestPaths = [],
  database,
  handlers = new Map(),
  sourceAgent = null,
  authenticate,
  resolveHost,
  resolveExecutionContext,
  dependencyHealth,
  workerId = "platform-agent-worker",
  defaultTimeoutMilliseconds = 30000
}) {
  if (!database || typeof authenticate !== "function" || typeof resolveHost !== "function") {
    throw new TypeError("A PostgreSQL database and trusted authentication and host resolvers are required.");
  }
  const catalog = JSON.parse(await readFile(catalogPath, "utf8"));
  const explicitManifests = await Promise.all(manifestPaths.map(async (path) =>
    JSON.parse(await readFile(path, "utf8"))
  ));
  const definitionManifests = await discoverAgentManifests(definitionsDirectory);
  const stores = createPostgresAgentStores(database);
  const persistedManifests = await stores.definitionStore.listLatest();
  const registry = new AgentRegistry({
    catalog,
    manifests: [...explicitManifests, ...definitionManifests, ...persistedManifests]
  });

  // Seed missing platform definitions on first startup and persist the latest
  // lifecycle state. Persisted rows are loaded last, so disabled or retired
  // platform decisions are not silently overwritten by checked-in templates.
  for (const summary of registry.list()) {
    const manifest = registry.getAgent(summary.agentId);
    await stores.definitionStore.register(manifest);
  }

  const registeredHandlers = new Map(handlers);
  if (sourceAgent) {
    for (const [key, handler] of createSourceAgentHandlers(sourceAgent)) {
      registeredHandlers.set(key, handler);
    }
  }

  const policyEngine = new PolicyEngine({ approvalStore: stores.approvalStore });
  const runtime = new AgentRuntime({
    registry,
    handlers: registeredHandlers,
    auditStore: stores.auditStore,
    idempotencyStore: stores.idempotencyStore,
    dependencyHealth,
    policyEngine,
    defaultTimeoutMilliseconds
  });
  const httpServer = createAgentHttpServer({
    runtime,
    registry,
    authenticate,
    resolveHost
  });
  const worker = resolveExecutionContext
    ? new AgentTaskWorker({
        workerId,
        queue: stores.taskQueue,
        runtime,
        resolveExecutionContext,
        auditStore: stores.auditStore
      })
    : null;

  return Object.freeze({
    registry,
    runtime,
    httpServer,
    worker,
    stores,
    listen(options) {
      return listenAgentHttpServer(httpServer, options);
    },
    async close() {
      if (httpServer.listening) {
        await new Promise((resolve, reject) => httpServer.close((error) => error ? reject(error) : resolve()));
      }
    }
  });
}
