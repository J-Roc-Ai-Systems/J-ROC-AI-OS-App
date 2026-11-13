import { readFile } from "node:fs/promises";
import { AgentRegistry } from "./agent-registry.mjs";
import { AgentRuntime } from "./agent-runtime.mjs";
import { PolicyEngine } from "./policy-engine.mjs";
import { AgentTaskWorker } from "./task-worker.mjs";
import { createAgentHttpServer } from "./http-gateway.mjs";
import { createPostgresAgentStores } from "./postgres-adapters.mjs";
import { createSourceAgentHandlers } from "./source-agent.mjs";

/**
 * Compose the host-neutral service. The caller owns the PostgreSQL connection
 * pool and must provide trusted authentication, host resolution, dependency
 * health, and idempotent single-use human approval integrations.
 */
export async function createPlatformAgentService({
  catalogPath,
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
  const fileManifests = await Promise.all(manifestPaths.map(async (path) =>
    JSON.parse(await readFile(path, "utf8"))
  ));
  const stores = createPostgresAgentStores(database);
  const persistedManifests = await stores.definitionStore.listLatest();
  const registry = new AgentRegistry({
    catalog,
    manifests: [...fileManifests, ...persistedManifests]
  });

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
    async listen(options) {
      const { listenAgentHttpServer } = await import("./http-gateway.mjs");
      return listenAgentHttpServer(httpServer, options);
    },
    async close() {
      if (httpServer.listening) {
        await new Promise((resolve, reject) => httpServer.close((error) => error ? reject(error) : resolve()));
      }
    }
  });
}
