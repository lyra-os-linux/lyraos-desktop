# Signed GNOME portal staging qualification — 2026-09-27

Issue [#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125) remains open.
The upstream success-response fix is now built and signed in
`home:rodrigosbrito:lyra:staging/xdg-desktop-portal-gnome`, target
`openSUSE_Leap_16.1/x86_64`, source revision **2** / srcmd5
`077471ed2335bc96dcb5b43fef6e1334`. Both ordinary and experimental supervised
GNOME sessions passed with the installed public RPM. **Release promotion,
installed-system migration and candidate ISO qualification remain pending.**
No host package, production parental policy or ISO was changed.

## Exact artifacts and build

`receipt.json`, `source.xml` and `revised-source-manifest.json` identify the OBS
sources. `signed-repository.json` gives public download URLs, sizes, SHA-256 and
DISTURL provenance. Large RPMs remain outside Git.

| Package | Version-release | SHA-256 |
| --- | --- | --- |
| xdg-desktop-portal-gnome (x86_64) | 48.0-160100.2.1.lyra1.160101.1 | `9e7f6622e12cc8c343f772b5900d4ca7e4be01c9a20ef9477cf24373e55b1670` |
| xdg-desktop-portal-gnome-lang (noarch) | 48.0-160100.2.1.lyra1.160101.1 | `ba84d6486f3b5907c86e0a38e17d93e939e0dbb674cd3ea4754deac256f50a28` |

The repository key fingerprint is
`399218A6E088C4053F4533BE58097F767EDCA82E`, pinned by the release manifest.
`signature-checks.json` records successful metadata GPG verification and both
RPM signatures using temporary key stores; no key was trusted on the host.
The public key and signed repomd snapshot are preserved. The installed backend
hash is `989bf8f785a09c1271830e48c60a5de91641148db172a037c84fde06e13074f8`.

The first clean OBS build exposed missing `BuildRequires: zstd`. OBS also
replaced a literal Release with `lp161.160100.1`, below the SUSE original.
Revision 2 declares zstd, preserves the SUSE prefix with the supported
`<CI_CNT>.<B_CNT>` placeholders, and supplies an OBS `.changes` history.
Portal source and upstream patch did not change. The installed RPM release
sorts above `160100.2.1` and below `160100.2.2` (actual RPM comparisons recorded).
`buildinfo.xml` is an OBS post-build snapshot: its next counter is not the
release of the signed artifact listed above.

`build-signed.log` records the successful GCC 13.4 build (trailing whitespace
normalized; original/copy hashes in `build-log-hashes.json`); rpmlint reports zero
errors and two warnings. SOURCE_DATE_EPOCH warnings remain; this is not a
reproducibility claim. `inspection.json` shows unchanged runtime requirements,
file inventory and service scriptlets. Only backend payload content differs.
The local GCC 15 artifact's additional GLIBC symbol requirement did not recur.

## Native qualification and restoration

- `transactions.json`: actual main+language upgrade, downgrade, dependency-checked
  removal and fresh install, then final return to the original signed SUSE RPM.
  Both installed candidate RPMs passed `rpm -V`. Language package and temporary
  signing key were removed; the original binary and trusted-key set were restored.
- `supervised/`: `signedFull1` passed the complete inherited regression, including
  native shortcut consent/activation/ownership/Close, ordinary keyboard input,
  files, permissions, audio, notifications, recording/decoding and screen lock.
  Zero audit loss/limiting and no persistent failed user units. Fixture source
  hashes are pinned in `generated-sources.json`; the adapter checks the installed
  RPM and does not replace its executable with a standalone build.
- `ordinary.json`: real GDM UID 1002 session in enforcing SELinux, stock provider
  and backend, unconfined client. Cancel left no bindings, Add enabled real
  Activated/Deactivated events, a foreign connection with the same app ID was
  denied List/Bind, and Close left no events after a further physical keypress.
  `ordinary-unit.json` records QMP phases and successful completion.
- `ordinary-restored.json` and supervised restoration records cover the fixture
  cleanup, including the ordinary home archive comparison. `verified-final.json`
  verifies 26 original RPMs, restored labels/temporary files and inactive GDM and
  auditd. SELinux returned to the disposable VM's initial permissive state.

## Solver findings and delivery gap

The two resolver reports contain actual zypper XML dry runs, first with the
candidate installed, then with the original SUSE package restored. Official
priority was 20 and staging 90, matching the installed-system priority pair;
the last forced-install probe raised staging to the image recipe priority 1.
These temporary changes and newly imported keys were restored after each run.
This is a two-repository VM simulation, not a complete installed Lyra or KIWI
image transaction. No solver dry run applied packages.

| Command/scenario | Original SUSE installed | Candidate installed |
| --- | --- | --- |
| `update PACKAGE` | No change: vendor and lower priority | No change |
| `update --repo STAGING PACKAGE` | No change: vendor | No change |
| `install --allow-vendor-change --from STAGING PACKAGE` | Selects candidate, one upgrade/vendor change | No change |
| Forced install with vendor change, priorities 20/90 | Selects candidate | Reinstalls candidate |
| Same forced install, priorities 20/1 | Selects candidate | Reinstalls candidate |

The normal vegad repository update path therefore **does not migrate an existing
SUSE installation** to this OBS vendor. Publication alone is insufficient.
Before promotion, prefer a corrected official SUSE package if available, or
review and qualify a package-specific migration and return-to-SUSE policy.
Do not solve this by globally relaxing vendor stickiness or changing priorities.
A dry run selecting a package is not evidence of an executed zypper migration,
future SUSE supersedence, or a fresh KIWI image's full dependency resolution.

## Release tooling and recheck

`staging_only_packages` requires this candidate's source inventory and successful
published build in staging. Release inventory remains unchanged; promote and
rollback commands reject this candidate as unowned. A reviewed manifest change
must transfer it to normal `packages` before revision-pinned promotion.
`gate-staging.txt` and `gate-release.txt` passed for all three managed projects.

From the repository root:

```sh
python3 docs/evidence/portal-staging/qualify.py
python3 docs/evidence/portal-rpm/qualify.py
python3 -m unittest discover -s tests -v
```

The offline qualifier checks collected evidence, source hashes, signed-artifact
identity, transaction results and exact solver selections; it regenerates and
runs the inherited supervised qualifier in a temporary directory. It does not
contact OBS or prove that mutable repository URLs still serve these bytes.
Live signature validation must download the exact artifacts, compare SHA-256
and verify signatures with the pinned key again. Historical local qualification
uses its archived `local-build.spec` and remains independent of recipe evolution.

Live fixture scripts require the marked disposable VM and fixed `/root` inputs.
Use `transactions.py prepare`, the inherited `portal-rpm/prepare-supervised.py`
and generated full driver, `run-ordinary.py WORKSPACE_ROOT UNIQUE_TAG`, resolver
`candidate`, transaction `restore`, resolver `original`, then final restoration
verification. Preserve the raw reports before running a new artifact/tag.

Registry app IDs still do not authenticate production application identity.
Adversarial APIs, account-wide admission and full parental integration remain
outside this delivery; #6/#102 stay open and production protection stays disabled.
