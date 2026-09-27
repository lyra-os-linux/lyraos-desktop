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
service's snapshot, authorization, offline execution and recovery flow. Its
current signed manifest authorizes vendor **pairs**, without a package scope.
A global SUSE-to-OBS pair would be too broad for this exception: add and test
package-scoped authorization before generating a migration manifest. The normal
vegad update command should retain its existing policy.

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
