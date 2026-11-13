import test from "node:test";
import assert from "node:assert/strict";
import { GitHubSourceCatalog, GitHubSourceInspector } from "../github-source-adapters.mjs";

function response(status, body) {
  return { ok: status >= 200 && status < 300, status, async json() { return body; } };
}

test("GitHub catalog discovers public repositories and captures immutable commit references", async () => {
  const calls = [];
  const catalog = new GitHubSourceCatalog({
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      if (url.includes("/search/repositories")) {
        return response(200, { items: [{
          full_name: "example/public-project",
          html_url: "https://github.com/example/public-project",
          default_branch: "main",
          private: false,
          language: "Kotlin",
          license: { spdx_id: "MIT" },
          topics: ["android"]
        }] });
      }
      return response(200, { sha: "a".repeat(40) });
    }
  });
  const results = await catalog.discover({
    query: "android repair",
    maxResults: 10,
    allowPrivateRepositoryAccess: false
  }, { tenantId: "tenant-1" });
  assert.equal(results.length, 1);
  assert.equal(results[0].checksum, "a".repeat(40));
  assert.equal(results[0].license, "MIT");
  assert.equal(calls[0].options.headers.authorization, undefined);
  assert.match(calls[0].url, /is%3Apublic/);
});

test("GitHub catalog requires Environment Agent and repository authorization for private access", async () => {
  const publicOnly = new GitHubSourceCatalog({ fetchImpl: async () => response(200, { items: [] }) });
  await assert.rejects(
    publicOnly.discover({ query: "private code", allowPrivateRepositoryAccess: true }),
    (error) => error.code === "SOURCE_ACCESS_DENIED"
  );

  let authorizedRepository = false;
  let credentialCallbackRan = false;
  const environmentAgent = {
    async withCredentials(input, callback) {
      credentialCallbackRan = input.references[0] === "github/source-token";
      return callback({ "github/source-token": "temporary-token-value" });
    }
  };
  const catalog = new GitHubSourceCatalog({
    environmentAgent,
    githubTokenReference: "github/source-token",
    resolveCredentialContext: async () => ({
      principal: {
        authenticated: true,
        principalId: "chairman",
        tenantId: "tenant-1",
        secretReferences: ["github/source-token"]
      },
      tenantId: "tenant-1"
    }),
    repositoryAuthorizer: async ({ repository }) => repository === "example/private-project",
    fetchImpl: async (url, options) => {
      assert.equal(options.headers.authorization, "Bearer temporary-token-value");
      if (url.includes("/search/repositories")) {
        return response(200, { items: [{
          full_name: "example/private-project",
          html_url: "https://github.com/example/private-project",
          default_branch: "main",
          private: true,
          language: "Kotlin",
          license: { spdx_id: "MIT" },
          topics: []
        }, {
          full_name: "other/private-project",
          html_url: "https://github.com/other/private-project",
          default_branch: "main",
          private: true,
          language: "Kotlin",
          license: { spdx_id: "MIT" },
          topics: []
        }] });
      }
      return response(200, { sha: "b".repeat(40) });
    }
  });
  const records = await catalog.discover({
    query: "device repair",
    maxResults: 10,
    allowPrivateRepositoryAccess: true
  }, { requestId: "req-1" });
  assert.equal(credentialCallbackRan, true);
  assert.equal(records.length, 1);
  assert.equal(records[0].name, "example/private-project");
  authorizedRepository = true;
  assert.equal(authorizedRepository, true);
});

test("GitHub inspector requires an approved license and immutable commit identifier", async () => {
  const inspector = new GitHubSourceInspector({ prohibitedLicenses: ["agpl-3.0"] });
  const approved = await inspector.inspect({
    license: "MIT",
    checksum: "c".repeat(40),
    language: "Kotlin"
  }, {
    allowedLicenses: ["MIT"],
    requiredLanguage: "Kotlin"
  });
  assert.equal(approved.compatible, true);
  assert.equal(approved.licenseRisk, "APPROVED");
  assert.equal(approved.checksumVerified, true);

  const prohibited = await inspector.inspect({
    license: "AGPL-3.0",
    checksum: "d".repeat(40),
    language: "Kotlin"
  }, { allowedLicenses: ["MIT"] });
  assert.equal(prohibited.licenseRisk, "PROHIBITED");

  const review = await inspector.inspect({
    license: null,
    checksum: null,
    language: "Java"
  }, { allowedLicenses: ["MIT"], requiredLanguage: "Kotlin" });
  assert.equal(review.compatible, false);
  assert.equal(review.licenseRisk, "UNKNOWN");
  assert.equal(review.checksumVerified, false);
});
