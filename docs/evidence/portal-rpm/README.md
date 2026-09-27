# Local GNOME portal RPM qualification — 2026-09-27

Issue [#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125) remains open.
The local candidate `xdg-desktop-portal-gnome-48.0-160100.2.1.lyra1.x86_64`
passed native tests in ordinary and experimental supervised GNOME sessions,
plus actual RPM installation, upgrade and rollback. It is **unsigned and not
published**. No host package or ISO was changed.

RPM SHA-256: `a4a5e1c0ebf5fa35b125e003190869f7c636c365b579d1109cacbf7ae1a43b30`.
Installed executable SHA-256:
`d3496c21d966d3c1813d14c4049c786601b2d51243432b09959347d009a52994`.

The exact historical spec is preserved in `local-build.spec`; subsequent OBS
packaging changes do not rewrite this qualification.

The [recipe](../../../packaging/xdg-desktop-portal-gnome/README.md) reuses the
signed SUSE source and libgxdp submodule and adds only the upstream fix.
`build.json` records a dependency-checked `rpmbuild -ba`, including source
signature validation and build warnings. `artifacts.json` identifies all binary,
language, debug and source RPM outputs. Large RPM files stay outside Git.

## What passed

- `inspection.json`: identical package file inventory and service scriptlets;
  only `/usr/libexec/xdg-desktop-portal-gnome` differs in payload content.
  The release suffix sorts above the affected SUSE release and below its next
  maintenance release. GCC 15 adds the automatic `GLIBC_2.38` symbol dependency;
  the tested Leap 16.1 glibc 2.40 provides it. This is not qualification for older
  bases or a prediction of the eventual OBS binary's dependencies.
- `transactions.json`: real upgrade to the candidate, downgrade to the signed
  original, dependency-checked removal, fresh candidate installation, and final
  downgrade. No `--nodeps`, `--force`, repository-priority change or package lock.
  `rpm -V` and the original executable checksum passed after rollback.
- `supervised/`: complete `rpmFull1` regression, with 31 static policy checks,
  actual native consent and keyboard signals, foreign-session denial, Close,
  files/permissions, notifications, recording/decoding, audio and lock. Zero
  audit loss/limiting and zero persistent failed user units. Recovery restored
  106 files. This run verifies the installed RPM; it never substitutes the
  earlier standalone build-tree executable.
- `ordinary.json`: native GDM UID 1002 session, stock provider/backend,
  enforcing SELinux and an unconfined ordinary client. Cancel leaves no
  bindings; real Add consent allows exactly one Activated/Deactivated pair;
  another connection using the same app ID cannot List/Bind; Close followed by
  another key press emits no new signals during the 10-second observation.
  `ordinary-unit.json` records QMP phases and successful service completion.
- `ordinary-restored.json`: home restored from an xattr/SELinux-aware archive
  and compared with it; GDM config restored, generated probe/desktop removed,
  user runtime gone. The initial diagnostic hit the GNOME login overview
  instead of the consent dialog; it restored successfully but did not pass.
  The final fixture explicitly closes the overview before dialog tests.
- `verified-final.json`: 26 original RPMs verified after restoring the signed
  SUSE portal package; supervised labels/temporaries restored, GDM and auditd
  inactive, SELinux back to the fixture's initial permissive state.

## Recheck collected evidence

From the repository root:

```sh
python3 docs/evidence/portal-rpm/qualify.py
```

The verifier regenerates the supervised fixture from the committed
`parental-shortcuts` sources, checks its complete source hashes against
`generated-sources.json`, and runs its original full qualifier in a temporary
directory. The adapter replaces only the standalone portal copy with NEVRA,
RPM-integrity and executable-hash assertions. It then checks transactions and
the ordinary session. Historical evidence is never overwritten.

To repeat live tests, use only the marked disposable parental VM. `build.py`
expects the original source RPM, recipe and upstream patch under the fixed
`/root` paths shown in the script. `transactions.py prepare` validates the exact
candidate hash and leaves it installed; `restore` returns to the signed original.
Generate a fresh supervised fixture with `prepare-supervised.py BASE OUTPUT`,
then use its `run.py TAG WORKSPACE_ROOT`. Run `run-ordinary.py WORKSPACE_ROOT TAG`
for the ordinary account. The ordinary fixture has a systemd runtime deadline
and ExecStopPost recovery. Reusing these scripts for a new RPM requires recording
and qualifying that new artifact explicitly.

## Remaining delivery gates

The local VM build is not an OBS release. Still required: the chosen package's
signed staging artifact, repository/vendor solver behavior under Lyra's existing
priorities, qualification of that exact artifact, reviewed promotion, and a
candidate ISO identified and tested by checksum. Prefer a corrected official
SUSE package if available at delivery time. Language/debug RPMs were built but
were not installed in this fixture. No automatic source-package inventory change
or package publication is included here.

These tests do not establish authenticated app identity, exhaustive shortcut
layouts/conflicts, locked-session revocation, or adversarial Screencast/PipeWire
isolation. #6/#102 and full parental-control integration remain open.
