import { mkdir, open } from "node:fs/promises";
import { dirname } from "node:path";
import { randomUUID } from "node:crypto";

const SECRET_KEY = /(password|secret|token|authorization|cookie|private.?key|api.?key)/i;

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (!value || typeof value !== "object") return value;
  const result = {};
  for (const [key, child] of Object.entries(value)) {
    result[key] = SECRET_KEY.test(key) ? "[REDACTED]" : redact(child);
  }
  return result;
}

/**
 * Local-development audit adapter only. Production deployments must inject a
 * tenant-aware database audit store with append-only permissions and backups.
 */
export class JsonLinesAuditStore {
  constructor(filePath) {
    if (!filePath) throw new TypeError("An audit file path is required.");
    this.filePath = filePath;
  }

  async append(event) {
    await mkdir(dirname(this.filePath), { recursive: true });
    const record = {
      ...redact(event),
      eventId: randomUUID(),
      recordedAt: new Date().toISOString()
    };
    const handle = await open(this.filePath, "a", 0o600);
    try {
      await handle.writeFile(`${JSON.stringify(record)}\n`, "utf8");
      await handle.sync();
    } finally {
      await handle.close();
    }
    return record.eventId;
  }
}
