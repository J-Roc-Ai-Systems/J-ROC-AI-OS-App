import { randomUUID } from "node:crypto";

function requireDatabase(database) {
  if (!database || typeof database.query !== "function") {
    throw new TypeError("A PostgreSQL-compatible database client with query(sql, params) is required.");
  }
  return database;
}

function redact(value) {
  const secretKey = /(password|secret|token|authorization|cookie|private.?key|api.?key)/i;
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== "object") return value;
  const output = {};
  for (const [key, child] of Object.entries(value)) {
    output[key] = secretKey.test(key) ? "[REDACTED]" : redact(child);
  }
  return output;
}

export class PostgresAgentDefinitionStore {
  constructor(database) { this.database = requireDatabase(database); }

  async listRegistered() {
    const result = await this.database.query(
      `select manifest
         from (
           select distinct on (agent_id) manifest, lifecycle_state
             from public.platform_agent_definitions
            order by agent_id, updated_at desc
         ) latest
        where lifecycle_state in ('registered','available','degraded','disabled')`
    );
    return (result.rows ?? []).map((row) => row.manifest);
  }

  async register(manifest) {
    if (!manifest?.agentId || !manifest?.version || !manifest?.lifecycleState) {
      throw new TypeError("A complete platform agent manifest is required.");
    }
    if (manifest.lifecycleState === "available" &&
        (manifest.health?.status !== "passed" || manifest.tests?.status !== "passed")) {
      throw new Error("An agent cannot be persisted as available before tests and readiness pass.");
    }
    const result = await this.database.query(
      `insert into public.platform_agent_definitions (agent_id, agent_version, lifecycle_state, manifest)
       values ($1,$2,$3,$4::jsonb)
       on conflict (agent_id, agent_version) do update
         set lifecycle_state = excluded.lifecycle_state,
             manifest = excluded.manifest,
             updated_at = clock_timestamp()
       returning agent_id, agent_version, lifecycle_state`,
      [manifest.agentId, manifest.version, manifest.lifecycleState, JSON.stringify(redact(manifest))]
    );
    return result.rows?.[0] ?? null;
  }
}

export class PostgresAuditStore {
  constructor(database) { this.database = requireDatabase(database); }

  async append(event) {
    const details = redact(event);
    const result = await this.database.query(
      `insert into public.platform_agent_audit_events
       (event_type, request_id, agent_id, agent_version, tenant_id, principal_id,
        capability, approval_id, result_status, details)
       values ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10::jsonb)
       returning event_id`,
      [
        String(event.event ?? "agent.event"),
        event.requestId ?? null,
        event.agentId ?? null,
        event.agentVersion ?? null,
        event.tenantId ?? null,
        event.principalId ?? null,
        event.capability ?? null,
        event.approvalId ?? null,
        event.resultStatus ?? null,
        JSON.stringify(details)
      ]
    );
    const eventId = result.rows?.[0]?.event_id;
    if (!eventId) throw new Error("Audit insert did not return an event identifier.");
    return eventId;
  }
}

export class PostgresApprovalStore {
  constructor(database) { this.database = requireDatabase(database); }

  async request(input) {
    const result = await this.database.query(
      `insert into public.platform_agent_approvals
       (tenant_id, request_id, agent_id, capability, principal_id, status, reason, expires_at)
       values ($1,$2,$3,$4,$5,'pending',$6,$7)
       returning approval_id`,
      [input.tenantId, input.requestId, input.agentId, input.capability,
       input.principalId, input.reason ?? null, input.expiresAt]
    );
    const approvalId = result.rows?.[0]?.approval_id;
    if (!approvalId) throw new Error("Approval request did not return an identifier.");
    return approvalId;
  }

  /**
   * The calling gateway must verify that approvedBy is an authorized human
   * approver before this database mutation is allowed.
   */
  async approve({ approvalId, approvedBy, reason }) {
    if (!approvalId || !approvedBy) throw new TypeError("Approval identifier and verified human approver are required.");
    const result = await this.database.query(
      `update public.platform_agent_approvals
          set status = 'approved', approved_by = $2, reason = $3
        where approval_id = $1 and status = 'pending'
          and expires_at > clock_timestamp()
        returning approval_id`,
      [approvalId, approvedBy, reason ?? null]
    );
    return Boolean(result.rows?.[0]?.approval_id);
  }

  async reject({ approvalId, rejectedBy, reason }) {
    if (!approvalId || !rejectedBy) throw new TypeError("Approval identifier and verified human reviewer are required.");
    const result = await this.database.query(
      `update public.platform_agent_approvals
          set status = 'rejected', approved_by = $2, reason = $3
        where approval_id = $1 and status = 'pending'
        returning approval_id`,
      [approvalId, rejectedBy, reason ?? null]
    );
    return Boolean(result.rows?.[0]?.approval_id);
  }

  async consume(input) {
    const result = await this.database.query(
      "select public.consume_platform_agent_approval($1,$2,$3,$4,$5,$6) as consumed",
      [input.approvalId, input.requestId, input.agentId, input.capability, input.tenantId, input.principalId]
    );
    return result.rows?.[0]?.consumed === true;
  }
}

export class PostgresIdempotencyStore {
  constructor(database, { leaseSeconds = 120 } = {}) {
    this.database = requireDatabase(database);
    this.leaseSeconds = leaseSeconds;
  }

  async begin({ tenantId, idempotencyKey, fingerprint }) {
    const result = await this.database.query(
      "select claim_state, cached_response from public.claim_platform_agent_idempotency($1,$2,$3,$4)",
      [tenantId, idempotencyKey, fingerprint, this.leaseSeconds]
    );
    const row = result.rows?.[0];
    if (!row) throw new Error("Idempotency claim returned no state.");
    return {
      state: row.claim_state,
      response: row.cached_response ?? undefined
    };
  }

  async complete({ tenantId, idempotencyKey, fingerprint, response }) {
    const result = await this.database.query(
      "select public.complete_platform_agent_idempotency($1,$2,$3,$4::jsonb) as completed",
      [tenantId, idempotencyKey, fingerprint, JSON.stringify(response)]
    );
    if (result.rows?.[0]?.completed !== true) {
      throw new Error("Idempotency reservation could not be completed.");
    }
  }

  async fail({ tenantId, idempotencyKey, fingerprint, errorCode }) {
    const result = await this.database.query(
      "select public.fail_platform_agent_idempotency($1,$2,$3,$4) as failed",
      [tenantId, idempotencyKey, fingerprint, errorCode]
    );
    return result.rows?.[0]?.failed === true;
  }
}

export class PostgresTaskQueue {
  constructor(database) { this.database = requireDatabase(database); }

  async enqueue({ tenantId, request }) {
    const result = await this.database.query(
      `insert into public.platform_agent_jobs
       (tenant_id, request_id, agent_id, agent_version, capability, payload)
       values ($1,$2,$3,$4,$5,$6::jsonb)
       returning job_id`,
      [
        tenantId, request.requestId, request.agentId, request.agentVersion,
        request.capability, JSON.stringify(redact(request))
      ]
    );
    const jobId = result.rows?.[0]?.job_id;
    if (!jobId) throw new Error("Queue insert did not return a job identifier.");
    return jobId;
  }

  async claim(workerId, leaseSeconds = 120) {
    const result = await this.database.query(
      "select * from public.claim_platform_agent_job($1,$2)",
      [workerId, leaseSeconds]
    );
    return result.rows?.[0] ?? null;
  }

  async complete({ jobId, workerId, result: jobResult }) {
    const result = await this.database.query(
      "select public.complete_platform_agent_job($1,$2,$3::jsonb) as completed",
      [jobId, workerId, JSON.stringify(redact(jobResult))]
    );
    return result.rows?.[0]?.completed === true;
  }

  async fail({ jobId, workerId, errorCode }) {
    const result = await this.database.query(
      "select public.fail_platform_agent_job($1,$2,$3) as failed",
      [jobId, workerId, errorCode]
    );
    return result.rows?.[0]?.failed === true;
  }
}

export function createPostgresAgentStores(database) {
  return Object.freeze({
    definitionStore: new PostgresAgentDefinitionStore(database),
    auditStore: new PostgresAuditStore(database),
    approvalStore: new PostgresApprovalStore(database),
    idempotencyStore: new PostgresIdempotencyStore(database),
    taskQueue: new PostgresTaskQueue(database)
  });
}

export function createLocalRequestId() {
  return randomUUID();
}
