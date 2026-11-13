# J-ROC AI Source Agent

**Agent ID:** `jrocai.source`  
**Version:** `1.0.0`  
**Status:** Foundation implementation

## Mission
Discover, retrieve, classify, validate, deduplicate, and document source materials for authorized J-ROC AI projects.

## Core responsibilities
- Search approved local sources, repositories, documentation, and package registries through injected adapters.
- Capture source origin, version, language, license, and checksum where available.
- Check platform and language compatibility.
- Reject incompatible or prohibited-license sources.
- Route unknown licenses, unverified checksums, and review-required sources to human review.
- Maintain an audit trail for discovery and validation decisions.
- Return validated source candidates to requesting engineering or factory agents.

## Workflow
1. Receive a scoped source request.
2. Discover sources only through authorized catalog adapters.
3. Deduplicate by checksum, falling back to origin.
4. Inspect compatibility, license risk, and checksum status.
5. Classify each source as validated, rejected, or awaiting review.
6. Record each decision in the audit log.
7. Return a structured result. Importing dependencies or changing production source requires separate human approval.

## Security and governance
- No secrets are stored in this agent, its manifest, source records, logs, or Android application.
- All credentials and tokens are obtained through the J-ROC AI Environment Agent at runtime.
- Never place provider keys in Kotlin, Gradle, assets, GitHub, or the APK.
- Never execute untrusted code as part of discovery or validation.
- Respect repository permissions, package terms, and license obligations.
- Do not silently replace existing project files. Missing files may be recreated only within the approved project scope.
- Source Agent does not independently merge pull requests, publish releases, or install dependencies.

## Android integration
The Kotlin implementation uses injected interfaces: `SourceCatalog`, `SourceInspector`, and `SourceAuditLog`. Network and repository implementations are separate adapters.

## Current limitations
The foundation defines the agent contract and orchestration logic. Live GitHub, local-file, documentation, and package-registry adapters; persistent audit storage; and automated tests must be added and verified before claiming end-to-end source retrieval is operational.
