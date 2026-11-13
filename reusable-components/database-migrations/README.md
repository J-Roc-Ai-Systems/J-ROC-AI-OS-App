# Database Migration Reusables

- Migrations are ordered and immutable after release.
- Every migration has a stable identifier recorded in the migration ledger.
- Prefer additive changes and preserve existing user data.
- Do not silently drop columns, tables or records.
- Validate upgrades from an empty database and every supported prior schema.
- Backups and restore verification are required before production migration.
