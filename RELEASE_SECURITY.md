# Android release security and signing

Release signing material is never committed to this repository and is never embedded as source literals.

## Required protected environment variables

Configure these values only in the approved build runner's encrypted secret store, administered through the J-ROC AI Environment Agent:

- `JROCAI_ANDROID_KEYSTORE_PATH`: runner-local path to the protected keystore file.
- `JROCAI_ANDROID_KEYSTORE_PASSWORD`: keystore password.
- `JROCAI_ANDROID_KEY_ALIAS`: signing key alias.
- `JROCAI_ANDROID_KEY_PASSWORD`: signing key password.

The release Gradle task checks that all four variables exist. Debug builds do not require signing secrets. The keystore file must be provisioned to the isolated runner through a protected secret-file mechanism and must not be written into the repository workspace, uploaded as a build artifact, or printed to logs.

## Release operator controls

1. Confirm the source revision and approved release record.
2. Confirm dependency review and software bill of materials are attached to the release record.
3. Provision signing material to an isolated runner from the Environment Agent secret store.
4. Run the signed release build in the approved pipeline.
5. Verify the package signature, package identifier, version, artifact digest and source revision.
6. Store the signed artifact in the protected artifact registry.
7. Require a separate human approval before distribution.
8. Retain the previous known-good artifact and a tested rollback procedure.

## Current boundary

This file documents the signing contract and the Gradle guard. It does not provision a keystore, execute a release build, verify a package signature, upload an artifact, deploy an update, or perform rollback. Those operations remain blocked until the isolated runner, artifact registry, approval and recovery workflow are implemented and validated.
