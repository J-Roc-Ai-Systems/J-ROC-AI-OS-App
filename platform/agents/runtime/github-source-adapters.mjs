import { AgentRuntimeError } from "./errors.mjs";

function normalizeLicense(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  return value.trim().toLowerCase();
}

export class GitHubSourceCatalog {
  constructor({
    environmentAgent = null,
    githubTokenReference = null,
    resolveCredentialContext = null,
    repositoryAuthorizer = null,
    apiBaseUrl = "https://api.github.com",
    fetchImpl = globalThis.fetch
  } = {}) {
    if (typeof fetchImpl !== "function") throw new TypeError("A Fetch-compatible HTTP adapter is required.");
    const base = new URL(apiBaseUrl);
    if (base.protocol !== "https:") throw new TypeError("GitHub API traffic must use HTTPS.");
    this.environmentAgent = environmentAgent;
    this.githubTokenReference = githubTokenReference;
    this.resolveCredentialContext = resolveCredentialContext;
    this.repositoryAuthorizer = repositoryAuthorizer;
    this.apiBaseUrl = base.toString().replace(/\/$/, "");
    this.fetchImpl = fetchImpl;
  }

  async #get(path, token = null) {
    const response = await this.fetchImpl(`${this.apiBaseUrl}${path}`, {
      method: "GET",
      headers: {
        accept: "application/vnd.github+json",
        "x-github-api-version": "2022-11-28",
        ...(token ? { authorization: `Bearer ${token}` } : {})
      }
    });
    if (!response.ok) {
      const code = response.status === 401 || response.status === 403
        ? "SOURCE_ACCESS_DENIED"
        : "SOURCE_PROVIDER_UNAVAILABLE";
      throw new AgentRuntimeError(code, "GitHub source discovery could not complete. Check repository authorization and provider availability.", response.status === 404 ? 404 : 502);
    }
    return response.json();
  }

  async #discover(request, context, token, allowPrivate) {
    const query = request.query.trim();
    const maxResults = Math.min(100, Math.max(1, request.maxResults ?? 20));
    const q = allowPrivate ? query : `${query} is:public`;
    const search = await this.#get(
      `/search/repositories?q=${encodeURIComponent(q)}&sort=updated&order=desc&per_page=${maxResults}`,
      token
    );
    const items = Array.isArray(search.items) ? search.items : [];
    const records = [];

    for (const item of items) {
      if (!item.full_name || !item.html_url || !item.default_branch) continue;
      if (item.private === true) {
        if (!allowPrivate || typeof this.repositoryAuthorizer !== "function") continue;
        const allowed = await this.repositoryAuthorizer({
          repository: item.full_name,
          tenantId: context.tenantId ?? null,
          principalId: context.principalId ?? null
        });
        if (allowed !== true) continue;
      }

      let commitSha = null;
      try {
        const commit = await this.#get(
          `/repos/${item.full_name.split("/").map(encodeURIComponent).join("/")}/commits/${encodeURIComponent(item.default_branch)}`,
          token
        );
        if (typeof commit.sha === "string" && /^[a-f0-9]{40,64}$/i.test(commit.sha)) {
          commitSha = commit.sha;
        }
      } catch {
        // Preserve the repository candidate for review; the inspector will not
        // approve a source whose immutable commit identifier is unavailable.
      }

      const topics = Array.isArray(item.topics) ? item.topics : [];
      const notes = [
        `Visibility: ${item.private ? "private" : "public"}`,
        `Default branch: ${item.default_branch}`,
        `Repository metadata supplied by GitHub API`,
        ...topics.slice(0, 12).map((topic) => `Topic: ${topic}`)
      ];
      records.push({
        id: `github:${item.full_name}${commitSha ? `@${commitSha}` : ""}`,
        name: item.full_name,
        origin: item.html_url,
        kind: "GITHUB_REPOSITORY",
        version: commitSha ?? item.default_branch,
        language: item.language ?? null,
        license: item.license?.spdx_id ?? null,
        checksum: commitSha,
        notes
      });
      if (records.length >= maxResults) break;
    }
    return records;
  }

  async discover(request, context = {}) {
    if (!request || typeof request.query !== "string" || !request.query.trim()) {
      throw new AgentRuntimeError("INVALID_INPUT", "A GitHub source query is required.", 400);
    }
    if (request.allowPrivateRepositoryAccess !== true) {
      return this.#discover(request, context, null, false);
    }

    if (!this.environmentAgent || !this.githubTokenReference ||
        typeof this.resolveCredentialContext !== "function" ||
        typeof this.repositoryAuthorizer !== "function") {
      throw new AgentRuntimeError("SOURCE_ACCESS_DENIED", "Private repository access is not configured through the Environment Agent.", 403);
    }
    const credentialContext = await this.resolveCredentialContext(context);
    if (!credentialContext?.principal || !credentialContext?.tenantId) {
      throw new AgentRuntimeError("AUTHENTICATION_REQUIRED", "A trusted GitHub credential context is required.", 401);
    }
    return this.environmentAgent.withCredentials({
      references: [this.githubTokenReference],
      principal: credentialContext.principal,
      purpose: "Read explicitly authorized GitHub repository metadata",
      tenantId: credentialContext.tenantId,
      taskId: context.requestId ?? null
    }, (credentials) => this.#discover(
      request,
      { ...context, tenantId: credentialContext.tenantId, principalId: credentialContext.principal.principalId },
      credentials[this.githubTokenReference],
      true
    ));
  }
}

export class GitHubSourceInspector {
  constructor({ prohibitedLicenses = [], compatibilityCheck = null } = {}) {
    this.prohibitedLicenses = new Set(prohibitedLicenses.map(normalizeLicense).filter(Boolean));
    this.compatibilityCheck = compatibilityCheck;
  }

  async inspect(source, request = {}) {
    const findings = [];
    const license = normalizeLicense(source.license);
    const allowedLicenses = new Set((request.allowedLicenses ?? []).map(normalizeLicense).filter(Boolean));

    let compatible = true;
    if (request.requiredLanguage && source.language?.toLowerCase() !== request.requiredLanguage.toLowerCase()) {
      compatible = false;
      findings.push(`Required language mismatch: expected ${request.requiredLanguage}.`);
    }
    if (this.compatibilityCheck) {
      compatible = compatible && await this.compatibilityCheck(source, request);
    }

    let licenseRisk = "UNKNOWN";
    if (license && this.prohibitedLicenses.has(license)) {
      licenseRisk = "PROHIBITED";
      findings.push(`License ${license} is prohibited by platform policy.`);
    } else if (license && allowedLicenses.has(license)) {
      licenseRisk = "APPROVED";
    } else if (license) {
      licenseRisk = "REVIEW_REQUIRED";
      findings.push("The repository license is not on the request's approved license list.");
    } else {
      findings.push("The GitHub repository has no verified SPDX license identifier.");
    }

    const checksumVerified = typeof source.checksum === "string" && /^[a-f0-9]{40,64}$/i.test(source.checksum);
    if (!checksumVerified) findings.push("An immutable Git commit identifier could not be verified.");

    return { compatible, licenseRisk, checksumVerified, findings };
  }
}
