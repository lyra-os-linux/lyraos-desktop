# Experimental registered system services and timers adapter

This gate adds inhibition and native revocation of a root-selected catalog of
system services and timers to ordinary admission withdrawal. It fixes the
prototype's known service/timer path: PAM withdrawal and logind termination
alone do not fence or revoke unguarded `User=` producers in system.slice.
It is not automatic discovery or qualification of every system unit.

`SystemUnits` requires a nonempty immutable catalog with canonical service and
timer names and timer targets inside that catalog. It verifies classification
and catalog before authorization and revalidates afterward under the UID's
shared snapshot lock. Inhibition installs persistent root-owned /dev/null
masks, fsyncs the mask directory, reloads systemd and checks both the filesystem
and systemd's loaded masked state. It does not infer that old processes exited.
Explicit authorized revocation verifies those fences, stops timers before
services, waits a bounded interval for the process observer and rechecks fences
and sources. Partial failures retain masks and the ordinary withdrawal barrier;
there is no unmask, enrollment, ordinary-role restoration or NSS mutation API.
Authorization is trusted test injection, not Polkit or an authenticated API.

The mask backend opens its root-owned directory without following symlinks,
rejects writable directories, validates names, never replaces unexpected files
or links, and rejects masks with multiple links. Existing valid masks are
idempotent. Root/admin remain trusted, and no claim is made about arbitrary
privileged root commands bypassing a mask or moving work into a different unit.
A durable global operation journal, reboot reconciliation, failure recovery
and association of each mask with a monotonic lifecycle revision are pending.

The native fixture creates four new target vendor units (plain, PAM-guarded and
timer-triggered sleep services plus a timer) and three new peer units. The
registered target namespace is closed: even an inactive extra definition in
that namespace refuses admission coverage. It verifies protected source bytes,
canonical IDs, absence of aliases/drop-ins/transient units, User/Group/PAMName/
KillMode properties when loaded, and the timer's target. These checks are only
for the controlled fixture namespace, not every manager, runtime, generator,
alias, template, socket, path or privileged execution route on a real system.
The payloads are ordinary-user sleep processes; no supervised MAC confinement
is claimed. Historical PAM/withdrawal/coordinator/manager sources are unchanged.

The final matrix passed 25 native controls. Unguarded target PIDs survived
withdrawal and logind termination. Denied inhibition created no masks; an extra
inactive producer or changed source refused the operation. Masks fenced future
execution while an old unguarded PID remained alive. Denied revocation retained
that PID and its masks. Authorized revocation stopped timer then services,
verified tracked kernel pidfds exited and no target scope/UID process remained,
while the peer service, user manager and proof remained unchanged. All four
masked target activations were rejected by systemd. The peer timer restarted
its own stopped service. Loss of one mask refused completion even with zero
processes; explicit authorized repair and retries preserved negative authority.
The full coordinator still rejected absent producer coverage, and the withdrawn
user manager remained denied by the exact earlier PAM cause.

Six additional native filesystem refusal controls passed in a private scratch
directory after restoration (Permissive, not another Enforcing matrix): partial
installation preserves the first mask and an unexpected original file;
retry retains the mask inode; wrong links, hard-linked masks, writable
directories and symlink directories are refused. Scratch files are removed.
364 repository tests passed, including 20 new decision/failure tests; test
doubles do not qualify real producer coverage.

The first native attempt failed at ten controls due to the fixture driver
passing bytes to Path.write_text when creating the unknown unit. Its exact
source, logs, exit 1 and passing cleanup are archived in failed-attempt-1. It is
not counted as a passed matrix. The driver uses write_bytes in the complete
final run. Supplemental checks do not require repeating that unchanged adapter
implementation's entire passing matrix.

All fixture unit paths were originally absent. Cleanup stops registered timers
and services, removes their masks/vendor files, restores the original PAM bytes
and mode, removes registry/PAM fixtures, stops test managers and returns to
Permissive. Independent checks verify account/vendor preservation, no fixture
units/masks, and no remaining processes in the reserved cgroups even if systemd
has unloaded the unit metadata. The restored VM is powered off. Root evidence
helpers/backups and normal home/journal side effects remain; this is not a
whole disk rollback or complete kernel audit.

No host, recipe, RPM, OBS or ISO change. No account creation, UID/GID/group
mutation, publication or activation of an ordinary role. No reboot, physical
power loss, alias/template/runtime-generator discovery or full system-unit
namespace qualification. Required producers are unchanged and unsupported
coverage remains blocking. GDM password/SSH from the preceding gate were not
rerun here or silently upgraded to full GDM coverage. Issues #6/#102 remain
open and parental controls remain NO-GO. Next: D-Bus activation and cron, then
remaining namespace/lifecycle/authentication/UI/release qualification.

Offline evidence check:
`python3 docs/evidence/parental-unit-adapter/verify-evidence.py`.
Regression suite: `python3 -m unittest discover -s tests`.
