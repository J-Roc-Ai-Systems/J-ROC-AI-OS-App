import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const migrationUrl = new URL("../../storage/postgres/001_platform_agent_runtime.sql", import.meta.url);

test("platform runtime migration includes durable registry, audit, approval, idempotency, and task records", async () => {
  const sql = await readFile(migrationUrl, "utf8");
  for (const table of [
    "platform_agent_definitions",
    "platform_agent_audit_events",
    "platform_agent_approvals",
    "platform_agent_idempotency",
    "platform_agent_jobs"
  ]) {
    assert.equal(sql.includes("create table if not exists public." + table + " ("), true);
  }
});

test("platform audit history is immutable and client roles have no direct table permissions", async () => {
  const sql = await readFile(migrationUrl, "utf8");
  assert.match(sql, /before update or delete on public\.platform_agent_audit_events/i);
  assert.match(sql, /revoke all on public\.platform_agent_audit_events from public, anon, authenticated/i);
  assert.match(sql, /grant select, insert on public\.platform_agent_audit_events to service_role/i);
});

test("approval, idempotency, and job claim functions are scoped and server-only", async () => {
  const sql = await readFile(migrationUrl, "utf8");
  for (const name of [
    "consume_platform_agent_approval",
    "claim_platform_agent_idempotency",
    "complete_platform_agent_idempotency",
    "claim_platform_agent_job",
    "complete_platform_agent_job"
  ]) {
    assert.equal(sql.includes("create or replace function public." + name + "("), true);
  }
  assert.match(sql, /for update skip locked/i);
  assert.match(sql, /tenant_id = p_tenant_id/i);
  assert.match(sql, /revoke all on function public\.claim_platform_agent_job/i);
});
