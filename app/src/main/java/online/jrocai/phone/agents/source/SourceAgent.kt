package online.jrocai.phone.agents.source

/** Network, repository credentials, and file-system access belong to injected platform adapters. */
interface SourceCatalog {
    suspend fun discover(request: SourceRequest): List<SourceRecord>
}

interface SourceInspector {
    suspend fun validate(source: SourceRecord, request: SourceRequest): SourceValidation
}

interface SourceAuditLog {
    suspend fun record(event: String, sourceId: String?, details: String)
}

class SourceAgent(
    private val catalog: SourceCatalog,
    private val inspector: SourceInspector,
    private val auditLog: SourceAuditLog
) {
    suspend fun run(request: SourceRequest): SourceAgentResult {
        require(request.query.isNotBlank()) { "A source search query is required." }
        require(request.maxResults in 1..100) { "maxResults must be between 1 and 100." }

        auditLog.record("source_search_started", null, request.query)
        val discovered = catalog.discover(request)
            .distinctBy { it.checksum ?: it.origin }
            .take(request.maxResults)

        val accepted = mutableListOf<SourceRecord>()
        val rejected = mutableListOf<SourceRecord>()
        val review = mutableListOf<SourceRecord>()

        for (source in discovered) {
            val validation = inspector.validate(source, request)
            val findings = source.notes + validation.findings
            val evaluated = when {
                !validation.compatible ||
                    validation.licenseRisk == SourceLicenseRisk.PROHIBITED ->
                    source.copy(status = SourceStatus.REJECTED, notes = findings)
                validation.licenseRisk == SourceLicenseRisk.REVIEW_REQUIRED ||
                    validation.licenseRisk == SourceLicenseRisk.UNKNOWN ||
                    validation.checksumVerified == false ->
                    source.copy(status = SourceStatus.NEEDS_REVIEW, notes = findings)
                else -> source.copy(status = SourceStatus.VALIDATED, notes = findings)
            }

            when (evaluated.status) {
                SourceStatus.VALIDATED -> accepted += evaluated
                SourceStatus.REJECTED -> rejected += evaluated
                else -> review += evaluated
            }
            auditLog.record("source_${evaluated.status.name.lowercase()}", source.id, findings.joinToString("; "))
        }

        val summary = "Discovered ${discovered.size}; accepted ${accepted.size}; " +
            "rejected ${rejected.size}; awaiting review ${review.size}."
        auditLog.record("source_search_completed", null, summary)
        return SourceAgentResult(request, discovered, accepted, rejected, review, summary)
    }
}
