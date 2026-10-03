# Durable operation ownership across real kernel reboots — 2026-10-03

19 native controls passed on the first execution, across three distinct boot
IDs and two orderly kernel reboots. Issues #6/#102 remain OPEN and full parental
protection remains **NO-GO**. No host, product PAM, recipe, RPM, OBS or ISO
changes. Disposable VM independently restored and powered off.

This gate reuses the exact `operations.py`, inventory reader, historical
withdrawal writer and C PAM guard already qualified in the
[process-crash gate](../parental-operation-journal/README.md). Their 455-test
Python baseline is referenced by hash rather than rerun for unchanged code.
New code consists only of isolated VM preparation, inspection and verification
helpers. No new enrollment, unblock, producer revocation or product API.

## Sequence and result

The marked Leap 16.1 VM requires both test kernel markers and the disposable
disk serial. Existing ordinaryuser UID1002 is the target and installeduser
UID1000 is the independent peer. Their identities, groups, passwords and MAC
mapping remain unchanged. Two real managers initially admit positive ordinary
proofs under Enforcing. A child process exits91 after the owned legacy-blocked
phase is fsynced, while the old managers remain active. The target positive
proof, blocked marker, legacy journal and owned journal all exist.

The driver enables lingering for both accounts and installs a VM-only oneshot
hook ordered before logind and the user managers. The first orderly reboot
ends QEMU (`-no-reboot`); relaunch starts a new kernel. The hook sets Enforcing
and only inspects the owner. It does not authorize, resume, publish or remove
any barrier. File hashes, modes, ownership, link counts, inventory and stable
lock inodes survive unchanged.

Automatic target admission fails with status224/MainPID0 and the causal PAM
fixture rejection. The peer manager starts automatically in the expected
unconfined context. A manual target retry also fails without changing the peer
PID. Recovery refuses another operation, denied authorization and a changed
inventory. Restoring the catalog after that negative case is an explicit
trusted-root fixture action, not an anti-rollback protocol or repair API.

Fresh authorization resumes the original operation, keeps its full identity,
proof and inventory binding, advances only to owned retired3 and legacy
retired2, and removes only the original target positive proof. The marker
remains. A subsequent target attempt is still denied and peer state unchanged.

Before the second real reboot, the completed state is captured and the hook
is configured to fail42 after setting Enforcing but before inspection. The
failure changes no proof, marker, journal, inventory or lock. Target lingering
and manual admission still fail; the peer starts normally. Fresh authorization
for the completed operation produces a read-only retry, preserving state and
the peer PID. Controls: preparation4 + first reboot9 + failed-hook reboot6 =19.

## Scope and restoration

Two orderly kernel reboots prove persistence for the prepared owned-blocked
and retired states. They do not emulate power loss, disk/fsync errors, rollback
or every process-crash boundary. The hook deliberately sets Enforcing before
failing: this does not qualify failure before MAC enforcement. The launcher
uses a direct kernel/initrd and `enforcing=0`; the fixture hook establishes
Enforcing before logind. Early boot, bootloader, ISO and automatic production
reconciliation remain unqualified.

Ending old managers during shutdown is not producer revocation. No whole
namespace coverage, producer quiescence, real GDM/password login, NSS mutation,
global monotonic revision, anti-rollback, Polkit or production journal migration
is established. Success still means only `AdmissionWithdrawnNoQuiescence`.

Cleanup disables/removes the hook and two lingering entries, terminates only
fixture users, restores original PAM bytes/mode and Permissive baseline, and
removes the fixture module, registry, proofs and inventory. Independent readers
verify PAM/vendor/passwd/group preservation, absent fixture paths, zero relevant
processes/managers/runtime/sessions, and disabled/inactive SSH. Root evidence
helpers/backups/logs remain; scoped cleanup is not full filesystem rollback or
complete kernel audit. No packages installed.

```sh
python3 docs/evidence/parental-operation-boot/verify-evidence.py
```

Next: bind persistent system-unit masks and D-Bus retirements to operation
ownership and blocked recovery. Global revision authority and complete producer
inventory/coverage remain necessary before lifecycle and product integration.
