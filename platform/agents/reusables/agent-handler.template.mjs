/**
 * Host-neutral handler pattern. Replace the example operation, keeping strict
 * input bounds, tenant scoping, cancellation, and the platform policy boundary.
 * Never read provider secrets directly; use the Environment Agent.
 */
export function createExampleAgentHandlers({ service }) {
  if (!service || typeof service.execute !== "function") {
    throw new TypeError("An approved service adapter is required.");
  }
  return new Map([
    ["jrocai.example-agent:example.read", async (input, context) => {
      if (context.signal.aborted) throw new Error("Task cancelled or timed out.");
      if (!input || typeof input.resourceId !== "string" || input.resourceId.length > 200) {
        throw new TypeError("A valid resource identifier is required.");
      }
      const result = await service.execute({
        resourceId: input.resourceId,
        tenantId: context.tenantId,
        signal: context.signal
      });
      return { result };
    }]
  ]);
}
