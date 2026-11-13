package online.jrocai.phone.agents.source

enum class SourceKind { LOCAL_FILE, GITHUB_REPOSITORY, DOCUMENTATION, PACKAGE_REGISTRY, ARCHIVE }
enum class SourceStatus { DISCOVERED, RETRIEVED, VALIDATED, REJECTED, NEEDS_REVIEW }
enum class SourceLicenseRisk { APPROVED, REVIEW_REQUIRED, PROHIBITED, UNKNOWN }

data class SourceRequest(
    val query: String,
    val targetPlatform: String? = null,
    val requiredLanguage: String? = null,
    val allowedLicenses: Set<String> = emptySet(),
    val includePrereleases: Boolean = false,
    val maxResults: Int = 20
)

data class SourceRecord(
    val id: String,
    val name: String,
    val origin: String,
    val kind: SourceKind,
    val version: String? = null,
    val language: String? = null,
    val license: String? = null,
    val checksum: String? = null,
    val status: SourceStatus = SourceStatus.DISCOVERED,
    val notes: List<String> = emptyList()
)

data class SourceValidation(
    val compatible: Boolean,
    val licenseRisk: SourceLicenseRisk,
    val checksumVerified: Boolean?,
    val findings: List<String>
)

data class SourceAgentResult(
    val request: SourceRequest,
    val discovered: List<SourceRecord>,
    val accepted: List<SourceRecord>,
    val rejected: List<SourceRecord>,
    val needsReview: List<SourceRecord>,
    val summary: String
)
