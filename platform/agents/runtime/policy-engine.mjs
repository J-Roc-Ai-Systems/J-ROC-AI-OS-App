import { AgentRuntimeError } from "./errors.mjs";

export class PolicyEngine {
  constructor({ approvalStore = null, clock = () => Date.now() } = {}) {
    this.approvalStore = approvalStore;
    this.clock = clock;
  }

  async authorize({ manifest, request, principal, host }) {
    if (!principal?.authenticated || !principal.principalId || !principal.tenantId) {
      throw new AgentRuntimeError("AUTHENTICATION_REQUIRED", "An authenticated platform identity is required.", 401);
    }
    if (request.tenantId !== principal.tenantId ||
        request.requestedBy?.principalId !== principal.principalId) {
      throw new AgentRuntimeError("TENANT_BOUNDARY_DENIED", "The request identity or tenant does not match the authenticated caller.", 403);
    }
    if (!host || !manifest.supportedHosts.includes(host)) {
      throw new AgentRuntimeError("HOST_NOT_SUPPORTED", "This agent is not registered for the requesting host.", 403);
    }

    const capability = manifest.capabilities.find((item) =>
      (typeof item === "string" ? item : item.id) === request.capability
    );
    if (!capability || !manifest.permissions.capabilities.includes(request.capability)) {
      throw new AgentRuntimeError("CAPABILITY_NOT_DECLARED", "The requested capability is not explicitly declared and permitted.", 403);
    }
    if (!Array.isArray(principal.grantedCapabilities) ||
        !principal.grantedCapabilities.includes(request.capability)) {
      throw new AgentRuntimeError("PERMISSION_DENIED", "The caller has not been granted this capability.", 403);
    }

    const risk = typeof capability === "string" ? "high" : (capability.risk ?? "high");
    const requiresApproval = risk === "high" || capability.requiresApproval === true;
    let approvalId = null;
    if (requiresApproval) {
      const suppliedApprovalId = request.approval?.approvalId;
      if (!suppliedApprovalId || !this.approvalStore?.consume) {
        throw new AgentRuntimeError("APPROVAL_REQUIRED", "This operation requires a valid, single-use human approval.", 409);
      }
      const approved = await this.approvalStore.consume({
        approvalId: suppliedApprovalId,
        requestId: request.requestId,
        agentId: request.agentId,
        capability: request.capability,
        tenantId: request.tenantId,
        principalId: principal.principalId,
        expiresAt: this.clock()
      });
      if (!approved) {
        throw new AgentRuntimeError("APPROVAL_REQUIRED", "The approval is missing, expired, already used, or does not match this request.", 409);
      }
      approvalId = suppliedApprovalId;
    }
    return Object.freeze({ allowed: true, approvalId, risk });
  }
}
