package online.jrocai.phone.agents.source

/** Security boundary for Source Agent integrations. */
object SourceAgentPolicy {
    const val AGENT_ID = "jrocai.source"
    const val DISPLAY_NAME = "J-ROC AI Source Agent"
    const val VERSION = "1.0.0"

    val requiredControls = setOf(
        "record_source_origin",
        "record_version_and_checksum_when_available",
        "verify_license_before_reuse",
        "review_unknown_licenses",
        "reject_prohibited_licenses",
        "deduplicate_by_checksum_or_origin",
        "audit_discovery_and_validation",
        "require_human_approval_before_dependency_or_source_import",
        "use_environment_agent_for_all_credentials",
        "never_commit_secrets_or_embed_provider_keys_in_apk"
    )

    val prohibitedActions = setOf(
        "read_unapproved_private_repositories",
        "bypass_repository_permissions",
        "execute_untrusted_source_code_during_discovery",
        "import_unreviewed_dependencies_automatically",
        "write_credentials_to_files_or_logs",
        "claim_a_source_was_verified_without_a_validation_result"
    )
}
