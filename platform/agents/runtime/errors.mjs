export class AgentRuntimeError extends Error {
  constructor(code, message, statusCode = 400, details = undefined) {
    super(message);
    this.name = "AgentRuntimeError";
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
  }
}

export function asAgentRuntimeError(error) {
  if (error instanceof AgentRuntimeError) return error;
  return new AgentRuntimeError("INTERNAL_ERROR", "The agent operation failed.", 500);
}
