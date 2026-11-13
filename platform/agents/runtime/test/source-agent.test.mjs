import test from "node:test";
import assert from "node:assert/strict";
import { SourceAgent } from "../source-agent.mjs";

test("Source Agent deduplicates sources, validates license and checksum, and audits decisions", async () => {
  const events = [];
  const catalog = {
    async discover() {
      return [
        { id: "a", origin: "https://example.invalid/a", checksum: "same", notes: [] },
        { id: "duplicate", origin: "https://mirror.invalid/a", checksum: "same", notes: [] },
        { id: "b", origin: "https://example.invalid/b", checksum: "other", notes: [] },
        { id: "c", origin: "https://example.invalid/c", checksum: "third", notes: [] }
      ];
    }
  };
  const inspector = {
    async inspect(source) {
      if (source.id === "a") return { compatible: true, licenseRisk: "APPROVED", checksumVerified: true, findings: [] };
      if (source.id === "b") return { compatible: true, licenseRisk: "UNKNOWN", checksumVerified: true, findings: ["License not identified"] };
      return { compatible: false, licenseRisk: "PROHIBITED", checksumVerified: false, findings: ["Unsupported source"] };
    }
  };
  const agent = new SourceAgent({
    catalog,
    inspector,
    auditStore: { async append(event) { events.push(event); return `audit-${events.length}`; } }
  });
  const result = await agent.run({ query: "sample source", maxResults: 10 }, { requestId: "r1", tenantId: "t1" });
  assert.equal(result.discovered.length, 3);
  assert.equal(result.accepted.length, 1);
  assert.equal(result.needsReview.length, 1);
  assert.equal(result.rejected.length, 1);
  assert.equal(events.at(-1).event, "source.discovery.completed");
});

test("Source Agent rejects invalid limits and empty queries", async () => {
  const agent = new SourceAgent({
    catalog: { async discover() { return []; } },
    inspector: { async inspect() { return {}; } },
    auditStore: { async append() { return "audit"; } }
  });
  await assert.rejects(agent.run({ query: " " }), (error) => error.code === "INVALID_INPUT");
  await assert.rejects(agent.run({ query: "source", maxResults: 101 }), (error) => error.code === "INVALID_INPUT");
});

test("Source Agent does not continue if audit persistence is unavailable", async () => {
  let discoveryCalled = false;
  const agent = new SourceAgent({
    catalog: { async discover() { discoveryCalled = true; return []; } },
    inspector: { async inspect() { return {}; } },
    auditStore: { async append() { throw new Error("audit unavailable"); } }
  });
  await assert.rejects(agent.run({ query: "source" }));
  assert.equal(discoveryCalled, false);
});
