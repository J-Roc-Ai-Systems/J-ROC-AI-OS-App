import test from "node:test";
import assert from "node:assert/strict";
import {
  PostgresAuditStore,
  PostgresApprovalStore,
  PostgresIdempotencyStore,
  PostgresTaskQueue
} from "../postgres-adapters.mjs";

function fakeDatabase(result) {
  const calls = [];
  return {
    calls,
    async query(sql, params) {
      calls.push({ sql, params });
      return typeof result === "function" ? result(sql, params) : result;
    }
  };
}

test("PostgreSQL audit adapter redacts credential fields before persistence", async () => {
  const db = fakeDatabase({ rows: [{ event_id: "audit-1" }] });
  const store = new PostgresAuditStore(db);
  assert.equal(await store.append({
    event: "test",
    tenantId: "tenant-1",
    apiKey: "do-not-store",
    details: { accessToken: "hidden", safe: "visible" }
  }), "audit-1");
  const json = JSON.parse(db.calls[0].params[9]);
  assert.equal(json.apiKey, "[REDACTED]");
  assert.equal(json.details.accessToken, "[REDACTED]");
  assert.equal(json.details.safe, "visible");
});

test("PostgreSQL approval adapter consumes only a matching approval", async () => {
  const db = fakeDatabase({ rows: [{ consumed: true }] });
  const store = new PostgresApprovalStore(db);
  const result = await store.consume({
    approvalId: "00000000-0000-4000-8000-000000000001",
    requestId: "r1",
    agentId: "jrocai.demo",
    capability: "demo.release",
    tenantId: "t1",
    principalId: "p1"
  });
  assert.equal(result, true);
  assert.match(db.calls[0].sql, /consume_platform_agent_approval/);
});

test("PostgreSQL idempotency adapter exposes atomic claim and completion states", async () => {
  const db = fakeDatabase((sql) => {
    if (sql.includes("claim_platform_agent_idempotency")) return { rows: [{ claim_state: "acquired", cached_response: null }] };
    return { rows: [{ completed: true }] };
  });
  const store = new PostgresIdempotencyStore(db);
  const key = { tenantId: "t1", idempotencyKey: "key-1", fingerprint: "fingerprint" };
  assert.equal((await store.begin(key)).state, "acquired");
  await store.complete({ ...key, response: { status: "completed" } });
  assert.equal(db.calls.length, 2);
});

test("PostgreSQL queue claims and completes work through database functions", async () => {
  const db = fakeDatabase((sql) => {
    if (sql.includes("claim_platform_agent_job")) return { rows: [{ job_id: "job-1", state: "running" }] };
    if (sql.includes("complete_platform_agent_job")) return { rows: [{ completed: true }] };
    return { rows: [{ job_id: "job-1" }] };
  });
  const queue = new PostgresTaskQueue(db);
  const id = await queue.enqueue({
    tenantId: "t1",
    request: { requestId: "r1", agentId: "jrocai.demo", agentVersion: "1.0.0", capability: "demo.read", password: "secret" }
  });
  assert.equal(id, "job-1");
  assert.equal((await queue.claim("worker-1")).state, "running");
  assert.equal(await queue.complete({ jobId: "job-1", workerId: "worker-1", result: { ok: true } }), true);
  const persistedPayload = JSON.parse(db.calls[0].params[5]);
  assert.equal(persistedPayload.password, "[REDACTED]");
});
