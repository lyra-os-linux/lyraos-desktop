# Portal vendor transition qualification — 2026-09-27

The exact signed staging portal RPMs passed **six real zypper transactions**:
upgrade, idempotent repeat and return to the original SUSE package, both without
translations and with the matching language RPM installed. Each dry-run plan
was checked before execution; complete inventories prove that unrelated packages
were unchanged. No production migration was enabled and #125 remains open.

The [delivery policy](../../portal-package-delivery.md) limits the exception to
the portal package names. The normal vegad update policy stays unchanged.

## Identity and scope

- Source branch starts at Desktop `f29cd1ca980782bf283ec698ceec8c791cbcc705`.
- `official-check.json` records a refreshed official repository and its package
  search. `official.json` records fresh main/language downloads, trusted
  signatures and hashes. The main RPM SHA-256 is
  `6613e7d4f1b3acd5c0f9a36636ec61e9cb57b6cc902b52d1e550b8605cfe486b`, identical
  to the affected original used by the fixture. This is not a fixed successor.
- Staging main SHA-256:
  `9e7f6622e12cc8c343f772b5900d4ca7e4be01c9a20ef9477cf24373e55b1670`;
  language SHA-256:
  `ba84d6486f3b5907c86e0a38e17d93e939e0dbb674cd3ea4754deac256f50a28`.
  These are the same [signed artifacts already qualified in both sessions](../portal-staging/README.md).
  No native session regression was repeated for this unchanged artifact.
- Original vendor: `SUSE LLC <https://www.suse.com/>`; candidate vendor:
  `obs://build.opensuse.org/home:rodrigosbrito`. Hash and signature checks precede
  package identity checks. Repository aliases are not vendor identities.

## What was executed

`exercise.py` runs only as root in the marked disposable VM, with GDM and both
users inactive. It checks the disk serial, known artifact/key hashes and trusted
RPM signatures, then calls zypper with explicit local RPM paths. Dependencies,
file-conflict checks and signatures remain enabled; no `--force` or `--nodeps`.
`--no-recommends` preserves translation-package absence. Existing translations
are upgraded/returned together with the main package.

The solver gate in `policy.py` checks exact editions, architectures, package
counts and actions, including the duplicate vendor-change annotations. It rejects
additional packages/removals, wrong vendor or direction, unknown actions, missing
identity, inconsistent main/language versions and changed translation presence.
`plan.xml` is an actual pre-migration native plan used by the adversarial parser
unit tests. The gate consumes verified RPM identities separately from solver XML.

| Round | Expected change | Result |
| --- | --- | --- |
| main-upgrade | SUSE → staging, main only | Passed |
| main-idempotent | Same candidate again, no changes | Passed |
| main-return | Staging → original SUSE, main only | Passed |
| translated-upgrade | SUSE → staging, main and language | Passed |
| translated-idempotent | Same two candidates again, no changes | Passed |
| translated-return | Staging → original SUSE, main and language | Passed |

Each round JSON preserves the dry-run XML, actual execution XML, installed
identities and full before/after inventories. `commands.json` records all
commands/return codes and confirms that the emergency RPM downgrade fallback
was not used: both successful returns were zypper transactions.

The fixture has a systemd runtime limit and independent ExecStopPost recovery.
A persistent baseline is written before mutations. The second scenario's original
language RPM is setup data installed with rpm; it is removed during cleanup to
restore initial absence. Recovery also restores the original trusted-key set.
`restored.json` confirms the complete package inventory and repository/config
hashes; `verified-final.json` confirms 26 original RPMs and prior fixture cleanup.
`unit.json` records successful inactive service completion; stderr is empty.
Fixture source SHA-256 values were compared with the actual guest files and
preserved in `source-hashes.json`.

The first harness attempt stopped before mutations because this minimal guest
has no `/etc/zypp/zypp.conf`. The final fixture records absent configuration as
`null` and verifies that it remains absent, rather than creating a config file.
That diagnostic attempt is not counted as a successful round.

## Recheck and limits

```sh
python3 docs/evidence/portal-transition/qualify.py
python3 -m unittest discover -s tests -p 'test_portal_transition_policy.py' -v
```

The qualifier checks both dry-run and actual solver output, package isolation,
idempotency, signatures' execution status, successful zypper return and restored
state. CI runs it without a VM or network. It does not redo signature checks on
binary RPMs absent from Git or make claims about future repository contents.

For a live repeat, use a fresh disposable guest state, place the four exact RPMs
and pinned key at the paths in `exercise.py`, copy `policy.py` beside that script,
and run it as a bounded systemd service with `ExecStopPost=... exercise.py recover`.
The report directory must be unused, preventing accidental overwrite of evidence.
Do not execute this fixture on an installed user's system.

This is a package transition test in an idle guest. It does not qualify live
desktop replacement, power loss, a full offline system upgrade or a future fixed
SUSE successor. Returning to the original restores its known shortcut bug.
Automatic delivery still requires package-scoped authorization in the existing
upgrade service, a reviewed signed migration/release manifest and its own
end-to-end recovery tests. Release promotion and the exact candidate ISO remain
pending. Parental protection remains experimental and disabled in production.
