# Desktop Alpha 8 evidence contracts

Alpha 8 follows the plan recorded in issue #28 (approved 2026-10-07): new
installation only, tested in virtual machines, no parental control. It keeps
the Alpha 7 baseline except `hardware-matrix`, and adds `i18n`. Run
`scripts/image-build.py required-test-results` after changing `release.toml`
to see the exact list for the current stage. Missing, malformed or failed
evidence always produces `NO-GO`.

Every result uses schema 1, its documented `mode`, `status: passed` and a
nonempty `checks` array whose entries have a stable `id` and `status: passed`.
Reports must not contain credentials, documents, biometric samples or
unnecessary personal data.

## `i18n-result.json`

The locale list is exactly `en-US`, `pt-BR`, `es-ES`, with `fallback: en-US`.
Checks cover every Lyra-owned interactive package marked localizable in
`i18n/inventory.json`; upstream-owned or text-free packages retain their
versioned `not-applicable` rationale.

## Declarations in the release notes

`upgrade-rehearsal`, `eca-digital` and `feature-freeze` are not structured
results in Alpha 8. The release notes
(`docs/releases/lyra-os-desktop-1.1-alpha.8.md`) must state instead:

- that Alpha 8 supports new installations only and that upgrading from
  Alpha 7 was not tested;
- that the candidate was qualified only in virtual machines;
- the ECA Digital scope: no parental control, no supervised account
  enrollment, no age signal to applications and no retained age evidence.
  The upstream `malcontent` package remains a dependency of GNOME Control
  Center; its presence is not Lyra enforcement and must not be described as
  protection (issue #102);
- the feature freeze: no new functionality after the plan was approved, and
  the coordinator's confirmation at publication that no P0 or P1 issue
  applicable to the shipped scope remains open. Any other state is `NO-GO`.

## Reversal

If these contracts reject valid historical Alpha 7 evidence, revert the
Alpha 8 wrapper and stage-aware changes while retaining the seven-result
baseline. Never weaken a failed check or fabricate a passing report to unblock
publication.
