# GNOME portal backport delivery policy

Issue [#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125) fixes the
GNOME 48 success response after shortcut consent. This policy is deliberately
limited to `xdg-desktop-portal-gnome` and, when already installed, its `-lang`
subpackage. It does not authorize a general vendor switch or enable parental
protection.

## Selection and package scope

Prefer an official SUSE build containing the upstream fix. The 2026-09-27
repository refresh still offered `48.0-160100.2.1`; a fresh signed RPM download
matched the exact original used in the reproduction. Current qualified
backport: staging `48.0-160100.2.1.lyra1.160101.1`. Source revision, key and both
artifact hashes are in [the signed staging evidence](evidence/portal-staging/README.md).
A new build or official successor needs its own artifact qualification.

Normal zypper/vegad updates preserve vendor stickiness. Do not change the global
vendor policy, add vendor-equivalence rules, raise repository priorities, force
a reinstall, or use `--nodeps` to deliver this patch. The proposed exception is
an explicit transaction selecting only verified portal RPMs by exact identity.
Preserve whether translations were installed; move the main and language
versions together when they are present. An unexpected installed version/vendor
is a stop condition, not a reason to force a downgrade.

Before execution, verify pinned artifact hashes, trusted signatures, installed
identity, and the complete solver plan. Reject additional packages, removals,
architecture/name changes, mismatched versions and unknown actions. Unchanged
state must yield an empty plan. Preserve repository configuration and the vendor
policy for all other packages. The [native transition evidence](evidence/portal-transition/README.md)
executes this contract in a disposable VM with the exact signed staging RPMs.
It is a qualification fixture, not an installed migration service.

## Reversal and eventual return to SUSE

Retain the original signed RPMs before any transition. A controlled reversal
selects only those originals and explicitly permits the downgrade/vendor return;
this was executed with and without translations. **That rollback restores the
known shortcut bug too.** It is a recovery route, not a fixed SUSE successor.
Do not infer that a larger SUSE version will automatically replace the OBS vendor.

When an official corrected successor becomes available, inspect its sources,
qualify the exact signed artifact and both sessions, then review a separate
package-scoped return transaction. Retire the backport only after installed
systems and the image recipe consume that successor. No permanent version lock
or epoch is introduced.

## Remaining integration gates

The real zypper transitions establish package-level feasibility; they do not
complete delivery to users. The automatic path must reuse the existing upgrade
service's snapshot, authorization, offline execution and recovery flow. The
published release Updater 0.2.5 authorizes vendor **pairs**, without a package
scope. A global SUSE-to-OBS pair would be too broad for this exception.

Updater 0.2.6 adds exact package scopes and was qualified in staging on
2026-09-27: signed RPM `lyra-upgrade-0.2.6-lp161.1.1.x86_64.rpm`, SHA256
`30740d14ec768d54e5444034411d89baa6480b0ec7804b265c1d42fd3da2d65e`, OBS revision 39
with srcmd5 `8263d6f2a9e64f2b2af9ee8f9a196730`. Its 133 Rust tests and the native
PackageKit regression with the extracted RPM worker and two reboots passed.
See the [Updater staging qualification](https://github.com/lyra-os-linux/lyraos-desktop-updater/blob/ca8f6d085ac1041c9e6b21091670ba059b79185e/docs/vendor-scope-staging-qualification.md)
and [structured evidence](https://github.com/lyra-os-linux/lyraos-desktop-updater/blob/ca8f6d085ac1041c9e6b21091670ba059b79185e/docs/vendor-scope-staging-evidence.json).
This qualifies the package and PackageKit coexistence; the real signed portal
migration has not been exercised.

Package scopes alone do not provide a same-release route or exclude unrelated
same-vendor updates. The maintainer chose to deliver this correction within the
existing Lyra 1.1 identity. Updater 0.2.7 implements an explicit signed
`PackageMigration` operation with `source == target`, exact source/target RPM
identity, repository and SHA256, and `if_installed` for translations. Its complete
solver plan must match the pending entries; no additional dependencies, removals,
downgrades or forced same-edition replacement are permitted. Repositories remain
unchanged, and confirmation, snapshot, offline execution and boot/rollback
verification use the existing service. See
[the implementation contract](https://github.com/lyra-os-linux/lyraos-desktop-updater/blob/9e861a2b5228b9e67d64baa786afdc8450c5e1de/docs/package-migration.md)
and [component qualification](https://github.com/lyra-os-linux/lyraos-desktop-updater/blob/9e861a2b5228b9e67d64baa786afdc8450c5e1de/docs/evidence/package-migration/README.md).

The local 0.2.7 binaries passed 145 Rust tests, 35 Python/UI tests, native signed
fixture RPM transitions, three cold boots for success and four for explicit
Snapper recovery. Signature/payload tampering blocked before application;
rollback restored inventory and retained the replay sequence. These tests use
inert packages, an ephemeral guest signing key and an authenticated UID fixture;
they do not qualify interactive Polkit or the actual portal migration.

Next, build and qualify the signed **0.2.7 OBS staging RPM**, then prepare the
reviewed portal manifest with `minimum_updater_version >= 0.2.7`, unchanged Lyra
identity and the exact artifact entries. Sign it through the existing release
key workflow and exercise the real portal with/without translations through the
Updater in a complete Btrfs baseline, including authorization and recovery.
The existing parental portal VM uses ext4 and is not that baseline. Staging
remains on 0.2.6 and release on 0.2.5 until their respective delivery gates pass;
do not raise the image minimum to an unavailable release RPM. The normal vegad
update command retains its existing policy.

A production transition must also handle running user sessions and service
restart/reboot behavior. The native fixture intentionally uses inactive GDM and
users; it does not qualify a live desktop replacement or interrupted system
upgrade. Do not attach package-manager calls to an RPM scriptlet or first-login
hook to bypass the upgrade service.

After that integration: reviewed staging-to-release ownership/promotion, actual
KIWI selection and dependency resolution, then install/update/rollback and
shortcut consent on the exact candidate ISO checksum. #125 stays open until
those gates pass. #6/#102 and full parental admission/adversarial coverage are
separate ongoing work.
