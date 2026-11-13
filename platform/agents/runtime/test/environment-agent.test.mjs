import test from "node:test";
import assert from "node:assert/strict";
import { EnvironmentAgent } from "../environment-agent.mjs";

test("Environment Agent scopes secrets to an adapter callback and audits only references", async () => {
  const events = [];
  const providerCalls = [];
  const agent = new EnvironmentAgent({
    credentialProvider: {
      async resolve(input) {
        providerCalls.push(input);
        return { value: "private-secret-value", expiresAt: Date.now() + 60000, scope: "read:repository" };
      }
    },
    auditStore: { async append(event) { events.push(event); } }
  });
  const principal = {
    authenticated: true,
    principalId: "worker-1",
    tenantId: "tenant-1",
    secretReferences: ["github/token"]
  };
  let observedSecret = false;
  const result = await agent.withCredentials({
    references: ["github/token"],
    principal,
    purpose: "read approved repository metadata",
    tenantId: "tenant-1",
    taskId: "task-1"
  }, async (credentials) => {
    observedSecret = credentials["github/token"] === "private-secret-value";
    return { fetched: true };
  });
  assert.deepEqual(result, { fetched: true });
  assert.equal(observedSecret, true);
  assert.equal(providerCalls.length, 1);
  assert.equal(events[0].event, "environment.secret_access.granted");
  assert.equal(JSON.stringify(events).includes("private-secret-value"), false);
});

test("Environment Agent rejects cross-tenant and unauthorized secret access", async () => {
  const events = [];
  const agent = new EnvironmentAgent({
    credentialProvider: { async resolve() { throw new Error("must not resolve"); } },
    auditStore: { async append(event) { events.push(event); } }
  });
  await assert.rejects(agent.withCredentials({
    references: ["github/token"],
    principal: { authenticated: true, principalId: "worker", tenantId: "tenant-a", secretReferences: [] },
    purpose: "test",
    tenantId: "tenant-a"
  }, async () => "nope"), (error) => error.code === "PERMISSION_DENIED");
  await assert.rejects(agent.withCredentials({
    references: ["github/token"],
    principal: { authenticated: true, principalId: "worker", tenantId: "tenant-a", secretReferences: ["github/token"] },
    purpose: "test",
    tenantId: "tenant-b"
  }, async () => "nope"), (error) => error.code === "PERMISSION_DENIED");
  assert.equal(events.length, 1);
  assert.equal(events[0].event, "environment.secret_access.denied");
});

test("Environment Agent rejects expired or empty credentials", async () => {
  const agent = new EnvironmentAgent({
    credentialProvider: { async resolve() { return { value: "", expiresAt: Date.now() - 10 }; } },
    auditStore: { async append() {} }
  });
  await assert.rejects(agent.withCredentials({
    references: ["service/key"],
    principal: { authenticated: true, principalId: "worker", tenantId: "t1", secretReferences: ["service/key"] },
    purpose: "test",
    tenantId: "t1"
  }, async () => "must-not-run"), (error) => error.code === "CREDENTIAL_UNAVAILABLE");
});
