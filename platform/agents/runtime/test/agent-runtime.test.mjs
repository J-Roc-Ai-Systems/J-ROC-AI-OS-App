import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { AgentRegistry } from "../agent-registry.mjs";
import { AgentRuntime } from "../agent-runtime.mjs";
import { PolicyEngine } from "../policy-engine.mjs";
import { AgentRuntimeError } from "../errors.mjs";

const catalog = {
  agents: [["demo", "Demo Agent", "Runtime test agent.", "testing"]]
};

function createManifest({
  lifecycleState = "available",
  risk = "low",
  capabilities = ["demo.read"],
  healthPassed = true,
  testsPassed = true,
  supportedHosts = ["cloud"],
  dependencies = []
} = {}) {
  return {
    manifestVersion: "1.0.0",
    agentId: "jrocai.demo",
    displayName: "Demo Agent",
    version: "1.0.0",
    scope: "platform-wide",
    owner: "J-ROC AI Platform",
    lifecycleState,
    capabilities: capabilities.map((id) => ({ id, risk })),
    supportedHosts,
    permissions: { capabilities, dataScopes: ["tenant"] },
    dependencies: { agents: dependencies },
    secrets: { environmentAgentManaged: true, secretReferences: [] },
    audit: { required: true, redactSecrets: true },
    health: { status: healthPassed ? "passed" : "pending" },
    tests: { status: testsPassed ? "passed" : "pending" },
    execution: { timeoutSeconds: 10 }
  };
}

function createHarness(options = {}) {
  const manifest = createManifest(options);
  const registry = new AgentRegistry({ catalog, manifests: [manifest] });
  const auditStore = options.auditStore ?? {
    events: [],
    async append(event) {
      this.events.push(event);
      return `audit-${this.events.length}`;
    }
  };
  const idempotencyStore = new Map();
  const handlers = new Map([
    ["jrocai.demo:demo.read", async () => ({ answer: 42, apiKey: "never-return-this" })],
    ["jrocai.demo:demo.release", async () => ({ releasePlan: "prepared" })]
  ]);
  const approvalStore = options.approvalStore ?? null;
  const runtime = new AgentRuntime({
    registry,
    handlers,
    auditStore,
    approvalStore,
    idempotencyStore: {
      async get(key) { return idempotencyStore.get(key); },
      async set(key, value) { idempotencyStore.set(key, value); }
    },
    dependencyHealth: { async isHealthy() { return true; } },
    policyEngine: new PolicyEngine({ approvalStore })
  });
  const principal = {
    authenticated: true,
    principalId: "chairman-1",
    tenantId: "tenant-1",
    grantedCapabilities: ["demo.read", ...((options.capabilities ?? []))]
  };
  const request = {
    requestId: "request-1",
    idempotencyKey: "idempotency-1",
    agentId: "jrocai.demo",
    agentVersion: "1.0.0",
    capability: options.requestCapability ?? (options.capabilities?.[0] ?? "demo.read"),
    tenantId: "tenant-1",
    requestedBy: { principalId: "chairman-1", principalType: "user" },
    input: { sample: true },
    approval: options.approvalId ? { approvalId: options.approvalId } : {}
  };
  return { registry, runtime, auditStore, handlers, principal, request };
}

test("canonical registry loads all 41 roles as non-executable specifications", async () => {
  const path = new URL("../../registry/agent-catalog.json", import.meta.url);
  const loaded = new AgentRegistry({ catalog: JSON.parse(await readFile(path, "utf8")) });
  assert.equal(loaded.size, 41);
  assert.equal(loaded.getAgent("jrocai.source").lifecycleState, "specified");
  assert.equal(loaded.list({ availableOnly: true }).length, 0);
});

test("registry refuses to mark an agent available before tests and readiness pass", () => {
  assert.throws(
    () => new AgentRegistry({ catalog, manifests: [createManifest({ healthPassed: false })] }),
    (error) => error.code === "AGENT_NOT_AVAILABLE"
  );
});

test("available registered capability is dispatched and sensitive output fields are redacted", async () => {
  const h = createHarness();
  const result = await h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" });
  assert.equal(result.status, "completed");
  assert.equal(result.output.answer, 42);
  assert.equal(result.output.apiKey, "[REDACTED]");
  assert.equal(h.auditStore.events.some((event) => event.event === "agent.execution.started"), true);
  assert.equal(h.auditStore.events.some((event) => event.event === "agent.execution.completed"), true);
});

test("catalog-only agent cannot execute", async () => {
  const h = createHarness({ lifecycleState: "registered" });
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "AGENT_NOT_AVAILABLE"
  );
});

test("caller without an exact capability grant is denied", async () => {
  const h = createHarness();
  h.principal.grantedCapabilities = [];
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "PERMISSION_DENIED"
  );
  assert.equal(h.auditStore.events.some((event) => event.event === "agent.execution.denied"), true);
});

test("tenant mismatch is rejected", async () => {
  const h = createHarness();
  h.request.tenantId = "another-tenant";
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "TENANT_BOUNDARY_DENIED"
  );
});

test("host adapter is checked against the agent manifest", async () => {
  const h = createHarness({ supportedHosts: ["android"] });
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "HOST_NOT_SUPPORTED"
  );
});

test("high-risk capability requires a request-bound human approval", async () => {
  const approvalStore = {
    async consume(input) {
      return input.approvalId === "approval-1" &&
        input.requestId === "request-1" &&
        input.tenantId === "tenant-1";
    }
  };
  const h = createHarness({
    capabilities: ["demo.release"],
    requestCapability: "demo.release",
    risk: "high",
    approvalStore,
    approvalId: "approval-1"
  });
  await assert.rejects(
    h.runtime.execute({
      request: { ...h.request, approval: {} },
      principal: h.principal,
      host: "cloud"
    }),
    (error) => error.code === "APPROVAL_REQUIRED"
  );
  const result = await h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" });
  assert.equal(result.status, "completed");
});

test("audit outage blocks handler execution", async () => {
  let invoked = false;
  const h = createHarness({
    auditStore: { async append() { throw new Error("storage unavailable"); } }
  });
  h.handlers.set("jrocai.demo:demo.read", async () => {
    invoked = true;
    return { ok: true };
  });
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "AUDIT_UNAVAILABLE"
  );
  assert.equal(invoked, false);
});

test("idempotency replays the first result and rejects a changed payload", async () => {
  const h = createHarness();
  let calls = 0;
  h.handlers.set("jrocai.demo:demo.read", async () => ({ count: ++calls }));
  const first = await h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" });
  const replay = await h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" });
  assert.deepEqual(replay, first);
  assert.equal(calls, 1);

  const savedGrants = h.principal.grantedCapabilities;
  h.principal.grantedCapabilities = [];
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "PERMISSION_DENIED"
  );
  h.principal.grantedCapabilities = savedGrants;

  await assert.rejects(
    h.runtime.execute({
      request: { ...h.request, input: { changed: true } },
      principal: h.principal,
      host: "cloud"
    }),
    (error) => error.code === "IDEMPOTENCY_CONFLICT"
  );
});

test("missing execution handler fails closed", async () => {
  const h = createHarness();
  h.handlers.clear();
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "AGENT_NOT_AVAILABLE"
  );
});

test("atomic idempotency reservations prevent duplicate concurrent execution", async () => {
  const h = createHarness();
  const records = new Map();
  h.runtime.idempotencyStore = {
    async begin({ tenantId, idempotencyKey, fingerprint }) {
      const key = `${tenantId}:${idempotencyKey}`;
      const current = records.get(key);
      if (!current) {
        records.set(key, { fingerprint, state: "running" });
        return { state: "acquired" };
      }
      if (current.fingerprint !== fingerprint) return { state: "conflict" };
      if (current.state === "completed") return { state: "completed", response: current.response };
      if (current.state === "failed") {
        current.state = "running";
        return { state: "acquired" };
      }
      return { state: "in_progress" };
    },
    async complete({ tenantId, idempotencyKey, fingerprint, response }) {
      records.set(`${tenantId}:${idempotencyKey}`, { fingerprint, state: "completed", response });
    },
    async fail({ tenantId, idempotencyKey, fingerprint }) {
      const current = records.get(`${tenantId}:${idempotencyKey}`);
      if (current?.fingerprint === fingerprint) current.state = "failed";
    }
  };
  let releaseHandler;
  let notifyStarted;
  const waitForRelease = new Promise((resolve) => { releaseHandler = resolve; });
  const started = new Promise((resolve) => { notifyStarted = resolve; });
  h.handlers.set("jrocai.demo:demo.read", async () => {
    notifyStarted();
    await waitForRelease;
    return { count: 1 };
  });

  const first = h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" });
  await started;
  await assert.rejects(
    h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" }),
    (error) => error.code === "REQUEST_IN_PROGRESS"
  );
  releaseHandler();
  const completed = await first;
  const replay = await h.runtime.execute({ request: h.request, principal: h.principal, host: "cloud" });
  assert.deepEqual(replay, completed);
});
