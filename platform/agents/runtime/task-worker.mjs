import { AgentRuntimeError } from "./errors.mjs";

/**
 * One durable queue consumer. resolveExecutionContext must re-check the
 * persisted task's requesting principal and host against trusted identity
 * infrastructure; a payload cannot establish its own authority.
 */
export class AgentTaskWorker {
  constructor({
    workerId,
    queue,
    runtime,
    resolveExecutionContext,
    auditStore,
    leaseSeconds = 120
  }) {
    if (!workerId || !queue?.claim || !queue?.complete || !queue?.fail ||
        !runtime?.execute || typeof resolveExecutionContext !== "function" || !auditStore?.append) {
      throw new TypeError("Worker identity, durable queue, runtime, trusted context resolver, and audit store are required.");
    }
    this.workerId = workerId;
    this.queue = queue;
    this.runtime = runtime;
    this.resolveExecutionContext = resolveExecutionContext;
    this.auditStore = auditStore;
    this.leaseSeconds = leaseSeconds;
  }

  async processOne() {
    const job = await this.queue.claim(this.workerId, this.leaseSeconds);
    if (!job) return { state: "idle" };

    try {
      const context = await this.resolveExecutionContext(job);
      if (!context?.principal?.authenticated || !context?.host) {
        throw new AgentRuntimeError("AUTHENTICATION_REQUIRED", "The durable task's caller context could not be verified.", 401);
      }
      const result = await this.runtime.execute({
        request: job.payload,
        principal: context.principal,
        host: context.host
      });
      const completed = await this.queue.complete({
        jobId: job.job_id ?? job.jobId,
        workerId: this.workerId,
        result
      });
      if (!completed) {
        await this.auditStore.append({
          event: "agent.job.completion_lease_lost",
          jobId: job.job_id ?? job.jobId,
          requestId: job.request_id ?? job.requestId,
          agentId: job.agent_id ?? job.agentId
        });
        return { state: "lease_lost" };
      }
      await this.auditStore.append({
        event: "agent.job.completed",
        jobId: job.job_id ?? job.jobId,
        requestId: job.request_id ?? job.requestId,
        agentId: job.agent_id ?? job.agentId
      });
      return { state: "completed", jobId: job.job_id ?? job.jobId, result };
    } catch (error) {
      const code = error instanceof AgentRuntimeError ? error.code : "AGENT_JOB_FAILED";
      await this.queue.fail({
        jobId: job.job_id ?? job.jobId,
        workerId: this.workerId,
        errorCode: code
      });
      await this.auditStore.append({
        event: "agent.job.failed",
        jobId: job.job_id ?? job.jobId,
        requestId: job.request_id ?? job.requestId,
        agentId: job.agent_id ?? job.agentId,
        errorCode: code
      });
      return { state: "failed_or_requeued", jobId: job.job_id ?? job.jobId, errorCode: code };
    }
  }
}
