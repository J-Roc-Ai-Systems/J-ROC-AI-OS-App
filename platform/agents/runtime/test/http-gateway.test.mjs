import test from "node:test";
import assert from "node:assert/strict";
import { createAgentHttpServer } from "../http-gateway.mjs";

test("HTTP gateway requires host authentication and never trusts caller identity fields", async (context) => {
  let invoked = false;
  const runtime = {
    async execute({ request, principal, host }) {
      invoked = true;
      assert.equal(principal.principalId, "verified-user");
      assert.equal(host, "web");
      assert.equal(request.requestedBy.principalId, "verified-user");
      return { status: "completed", requestId: request.requestId };
    }
  };
  const registry = {
    list({ host, availableOnly }) {
      assert.equal(host, "web");
      assert.equal(availableOnly, true);
      return [{ agentId: "jrocai.demo" }];
    }
  };
  const server = createAgentHttpServer({
    runtime,
    registry,
    authenticate: async (request) => request.headers.authorization === "Bearer test"
      ? { authenticated: true, principalId: "verified-user" }
      : null,
    resolveHost: async () => "web"
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  context.after(() => new Promise((resolve) => server.close(resolve)));
  const address = server.address();
  const base = `http://127.0.0.1:${address.port}`;

  const denied = await fetch(`${base}/v1/agents`);
  assert.equal(denied.status, 401);

  const listed = await fetch(`${base}/v1/agents`, { headers: { authorization: "Bearer test" } });
  assert.deepEqual(await listed.json(), { agents: [{ agentId: "jrocai.demo" }] });

  const response = await fetch(`${base}/v1/execute`, {
    method: "POST",
    headers: { authorization: "Bearer test", "content-type": "application/json" },
    body: JSON.stringify({ requestId: "r1", requestedBy: { principalId: "verified-user" } })
  });
  assert.equal(response.status, 200);
  assert.equal((await response.json()).status, "completed");
  assert.equal(invoked, true);
});
