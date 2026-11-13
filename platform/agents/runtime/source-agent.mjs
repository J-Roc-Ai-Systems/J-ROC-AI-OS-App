import { AgentRuntimeError } from "./errors.mjs";

export class SourceAgent {
  constructor({ catalog, inspector, auditStore }) {
    if (!catalog?.discover || !inspector?.inspect || !auditStore?.append) {
      throw new TypeError("Source catalog, inspector, and audit store adapters are required.");
    }
    this.catalog = catalog;
    this.inspector = inspector;
    this.auditStore = auditStore;
  }

  async run(request, context = {}) {
    if (!request || typeof request.query !== "string" || !request.query.trim()) {
      throw new AgentRuntimeError("INVALID_INPUT", "A non-empty source search query is required.", 400);
    }
    const maxResults = request.maxResults ?? 20;
    if (!Number.isInteger(maxResults) || maxResults < 1 || maxResults > 100) {
      throw new AgentRuntimeError("INVALID_INPUT", "maxResults must be between 1 and 100.", 400);
    }

    await this.auditStore.append({
      event: "source.discovery.started",
      requestId: context.requestId ?? null,
      tenantId: context.tenantId ?? null,
      queryLength: request.query.length
    });

    const discovered = await this.catalog.discover({
      query: request.query,
      targetPlatform: request.targetPlatform ?? null,
      requiredLanguage: request.requiredLanguage ?? null,
      allowedLicenses: Array.isArray(request.allowedLicenses) ? request.allowedLicenses : [],
      includePrereleases: request.includePrereleases === true,
      maxResults
    });
    const unique = [];
    const seen = new Set();
    for (const source of discovered ?? []) {
      const key = source.checksum ? `checksum:${source.checksum}` : `origin:${source.origin}`;
      if (source.origin && !seen.has(key)) {
        seen.add(key);
        unique.push(source);
      }
      if (unique.length >= maxResults) break;
    }

    const accepted = [];
    const rejected = [];
    const needsReview = [];
    for (const source of unique) {
      const validation = await this.inspector.inspect(source, request);
      const findings = [...(source.notes ?? []), ...(validation.findings ?? [])];
      let evaluated;
      if (!validation.compatible || validation.licenseRisk === "PROHIBITED") {
        evaluated = { ...source, status: "REJECTED", notes: findings };
        rejected.push(evaluated);
      } else if (validation.licenseRisk !== "APPROVED" || validation.checksumVerified !== true) {
        evaluated = { ...source, status: "NEEDS_REVIEW", notes: findings };
        needsReview.push(evaluated);
      } else {
        evaluated = { ...source, status: "VALIDATED", notes: findings };
        accepted.push(evaluated);
      }
      await this.auditStore.append({
        event: "source.validation.completed",
        requestId: context.requestId ?? null,
        tenantId: context.tenantId ?? null,
        sourceId: source.id ?? null,
        status: evaluated.status,
        licenseRisk: validation.licenseRisk
      });
    }

    const summary = `Discovered ${unique.length}; accepted ${accepted.length}; rejected ${rejected.length}; awaiting review ${needsReview.length}.`;
    await this.auditStore.append({
      event: "source.discovery.completed",
      requestId: context.requestId ?? null,
      tenantId: context.tenantId ?? null,
      discoveredCount: unique.length,
      acceptedCount: accepted.length,
      rejectedCount: rejected.length,
      reviewCount: needsReview.length
    });
    return { discovered: unique, accepted, rejected, needsReview, summary };
  }
}

export function createSourceAgentHandlers(sourceAgent) {
  if (!sourceAgent?.run) throw new TypeError("A Source Agent implementation is required.");
  return new Map([
    ["jrocai.source:source.discover", (input, context) => sourceAgent.run(input, context)]
  ]);
}
