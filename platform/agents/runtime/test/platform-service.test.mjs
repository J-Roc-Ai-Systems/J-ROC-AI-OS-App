import test from "node:test";
import assert from "node:assert/strict";
import { createPlatformAgentService } from "../platform-service.mjs";

test("platform service requires authenticated host integrations and PostgreSQL", async () => {
  await assert.rejects(createPlatformAgentService({}), /PostgreSQL database/);
});

test("platform service composes the shared registry and host-neutral gateway", async () => {
  const database = {
    async query(sql) {
      if (sql.includes("select distinct on")) return { rows: [] };
      return { rows: [{ event_id: "event-1", completed: true, claim_state: "acquired" }] };
    }
  };
  const service = await createPlatformAgentService({
    catalogPath: new URL("../../registry/agent-catalog.json", import.meta.url),
    database,
    authenticate: async () => null,
    resolveHost: async () => "cloud",
    resolveExecutionContext: async () => ({ principal: null, host: null }),
    dependencyHealth: { async isHealthy() { return false; } }
  });
  assert.equal(service.registry.size, 41);
  const listedAgents = service.registry.list();
  assert.equal(listedAgents.length, 41);
  assert.equal(listedAgents.filter((agent) => agent.lifecycleState === "registered").length, 1);
  assert.equal(service.registry.getAgent("jrocai.source").lifecycleState, "registered");
  assert.equal(service.registry.list({ availableOnly: true }).length, 0);
  assert.equal(service.httpServer.listening, false);
  assert.ok(service.worker);
  await service.close();
});
