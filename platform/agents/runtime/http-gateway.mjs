import { createServer } from "node:http";
import { AgentRuntimeError, asAgentRuntimeError } from "./errors.mjs";

function sendJson(response, statusCode, value) {
  const body = JSON.stringify(value);
  response.writeHead(statusCode, {
    "content-type": "application/json; charset=utf-8",
    "content-length": Buffer.byteLength(body),
    "cache-control": "no-store",
    "x-content-type-options": "nosniff"
  });
  response.end(body);
}

async function readJson(request, maximumBytes) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > maximumBytes) throw new AgentRuntimeError("INVALID_INPUT", "Request body exceeds the configured size limit.", 413);
    chunks.push(chunk);
  }
  try {
    return JSON.parse(Buffer.concat(chunks).toString("utf8"));
  } catch {
    throw new AgentRuntimeError("INVALID_INPUT", "Request body must be valid JSON.", 400);
  }
}

/**
 * Host-neutral HTTP adapter. Authentication and host identity must come from
 * trusted platform integrations; caller-supplied identity headers are ignored.
 */
export function createAgentHttpServer({
  runtime,
  registry,
  authenticate,
  resolveHost,
  maximumBodyBytes = 1024 * 1024
}) {
  if (!runtime || !registry || typeof authenticate !== "function" || typeof resolveHost !== "function") {
    throw new TypeError("Runtime, registry, authentication, and trusted host resolvers are required.");
  }

  return createServer(async (request, response) => {
    try {
      const url = new URL(request.url ?? "/", "http://localhost");
      if (request.method === "GET" && url.pathname === "/health") {
        return sendJson(response, 200, { service: "jrocai.platform.agent-runtime", status: "ok" });
      }

      const principal = await authenticate(request);
      if (!principal?.authenticated) {
        throw new AgentRuntimeError("AUTHENTICATION_REQUIRED", "Valid platform authentication is required.", 401);
      }
      const host = await resolveHost(request, principal);
      if (typeof host !== "string" || !host) {
        throw new AgentRuntimeError("HOST_NOT_SUPPORTED", "The requesting application host could not be verified.", 403);
      }

      if (request.method === "GET" && url.pathname === "/v1/agents") {
        return sendJson(response, 200, {
          agents: registry.list({ host, availableOnly: true })
        });
      }
      if (request.method === "POST" && url.pathname === "/v1/execute") {
        const body = await readJson(request, maximumBodyBytes);
        const result = await runtime.execute({ request: body, principal, host });
        return sendJson(response, 200, result);
      }
      throw new AgentRuntimeError("NOT_FOUND", "The requested endpoint does not exist.", 404);
    } catch (error) {
      const safe = asAgentRuntimeError(error);
      return sendJson(response, safe.statusCode, {
        error: { code: safe.code, message: safe.message }
      });
    }
  });
}

/** Bind to loopback by default; expose externally only behind trusted TLS/auth infrastructure. */
export async function listenAgentHttpServer(server, { host = "127.0.0.1", port = 8788 } = {}) {
  await new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, host, resolve);
  });
  return server.address();
}
