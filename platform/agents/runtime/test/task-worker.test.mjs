import test from "node:test";
import assert from "node:assert/strict";
import { AgentTaskWorker } from "../task-worker.mjs";

test("task worker verifies persisted caller context before runtime dispatch", async () => {
  const events = [];
  let executed = false;
  const job = {
    job_id: "job-1",
    request_id: "request-1",
    agent_id: "jrocai.demo",
    payload: { requestId: "request-1" }
  };
  const worker = new AgentTaskWorker({
    workerId: "worker-1",
    queue: {
      async claim() { return job; },
      async complete(input) { events.push(["complete", input]); return true; },
      async fail(input) { events.push(["fail", input]); return true; }
    },
    runtime: {
      async execute(input) {
        executed = true;
        assert.equal(input.principal.principalId, "verified");
        assert.equal(input.host, "cloud");
        return { status: "completed" };
      }
    },
    resolveExecutionContext: async () => ({
      principal: { authenticated: true, principalId: "verified" },
      host: "cloud"
    }),
    auditStore: { async append(event) { events.push(event); } }
  });
  const result = await worker.processOne();
  assert.equal(result.state, "completed");
  assert.equal(executed, true);
  assert.equal(events.some((event) => event.event === "agent.job.completed"), true);
});

test("task worker fails closed when persisted caller identity cannot be verified", async () => {
  let runtimeCalled = false;
  let failureRecorded = false;
  const worker = new AgentTaskWorker({
    workerId: "worker-2",
    queue: {
      async claim() { return { job_id: "job-2", payload: {} }; },
      async complete() { return true; },
      async fail() { failureRecorded = true; return true; }
    },
    runtime: { async execute() { runtimeCalled = true; } },
    resolveExecutionContext: async () => ({ principal: null, host: null }),
    auditStore: { async append() {} }
  });
  const result = await worker.processOne();
  assert.equal(result.state, "failed_or_requeued");
  assert.equal(runtimeCalled, false);
  assert.equal(failureRecorded, true);
});
