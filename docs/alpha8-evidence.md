# Desktop Alpha 8 evidence contracts

Alpha 8 extends the existing release evidence without changing the Alpha 7
baseline. Run `scripts/image-build.py required-test-results` after changing
`release.toml` to see the exact list for the current stage. Missing, malformed
or failed evidence always produces `NO-GO`.

Every result uses schema 1, its documented `mode`, `status: passed` and a
nonempty `checks` array whose entries have a stable `id` and `status: passed`.
Reports must not contain credentials, documents, biometric samples or
unnecessary personal data.

## `upgrade-rehearsal-result.json`

This result is emitted only after a published baseline has consumed a signed
successor manifest using real candidate repositories and RPMs, applied the
transaction offline, rebooted, verified the target and restored the baseline.
Its final `phase` is `rollback-verified`. The `facts` object records distinct
`baseline_version` and `target_version`, `manifest_signature_verified: true`,
`offline_applied: true`, a positive `reboot_count`,
`rollback_baseline_verified: true`, and these fault scenarios:

- `network-loss`;
- `low-space`;
- `ui-terminated`;
- `state-truncated`;
- `rpm-failure`;
- `initramfs-failure`.

The workflow must remain recoverable after each injected failure. Mocks may
test parsers and state transitions, but cannot produce release evidence.

## `eca-digital-result.json`

The result references nonempty `legal_review`, `security_review` and
`privacy_impact_assessment` records. It covers exactly `en-US`, `pt-BR` and
Spanish (`es-ES`), records `negative_and_evasion_tests: true`, and records
`retains_sensitive_age_evidence: false`. Checks cover the applicable account,
installation, bypass, age-signal, recovery, accessibility and data-minimization
cases. A missing applicable safeguard is a failed check, never an exception.

## `i18n-result.json`

The locale list is exactly `en-US`, `pt-BR`, `es-ES`, with `fallback: en-US`.
Checks cover every Lyra-owned interactive package marked localizable in
`i18n/inventory.json`; upstream-owned or text-free packages retain their
versioned `not-applicable` rationale.

## `feature-freeze-result.json`

This is a release-coordinator decision record, not an automatic claim. `GO`
requires `open_p0: 0`, `open_p1: 0`, the fixed three-locale list,
`all_features_implemented_or_removed: true` and
`documentation_consistent: true`. If any condition is absent, Alpha continues.

## Reversal

If these contracts reject valid historical Alpha 7 evidence, revert the
Alpha 8 wrapper and stage-aware additions while retaining the seven-result
baseline. Never weaken a failed check or fabricate a passing report to unblock
publication.
