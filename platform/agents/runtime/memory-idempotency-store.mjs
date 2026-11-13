/**
 * Test-only implementation. Never use in production: state is not shared,
 * durable, tenant-backed, or safe across process restarts.
 */
export class MemoryIdempotencyStore {
  #records = new Map();

  async begin({ tenantId, idempotencyKey, fingerprint }) {
    const key = `${tenantId}:${idempotencyKey}`;
    const record = this.#records.get(key);
    if (!record) {
      this.#records.set(key, { fingerprint, state: "running" });
      return { state: "acquired" };
    }
    if (record.fingerprint !== fingerprint) return { state: "conflict" };
    if (record.state === "completed") return { state: "completed", response: record.response };
    if (record.state === "failed") {
      record.state = "running";
      return { state: "acquired" };
    }
    return { state: "in_progress" };
  }

  async complete({ tenantId, idempotencyKey, fingerprint, response }) {
    const record = this.#records.get(`${tenantId}:${idempotencyKey}`);
    if (!record || record.fingerprint !== fingerprint || record.state !== "running") {
      throw new Error("No matching idempotency reservation is active.");
    }
    record.state = "completed";
    record.response = response;
  }

  async fail({ tenantId, idempotencyKey, fingerprint }) {
    const record = this.#records.get(`${tenantId}:${idempotencyKey}`);
    if (!record || record.fingerprint !== fingerprint || record.state !== "running") return false;
    record.state = "failed";
    return true;
  }
}
