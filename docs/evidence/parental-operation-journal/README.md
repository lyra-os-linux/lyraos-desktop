# Experimental durable withdrawal ownership — 2026-10-03

31 native controls and 455 Python tests passed (22 new decision/schema tests).
The eight subprocess crash boundaries passed on the first native execution.
Issues #6/#102 remain OPEN and full parental protection remains **NO-GO**.
No host, product PAM, recipe, RPM, OBS or ISO changes. The disposable VM was
independently inspected, restored and powered off, QEMU exit0.

## Behavior and boundaries

`Operations` binds admission withdrawal to an operation ID, the full local
user/UID/GID/group tuple, positive-proof hash and snapshot, and the inventory
revision/digest. Its only action is `withdraw-admission`. A partial inventory
can authorize this negative action; it cannot establish whole-account coverage.
There is no enrollment, activation, unblock or producer-revocation API.

Planning and execution recheck inventory, identity and proof state. Authorization
runs outside the storage locks, receives a detached copy, and must return literal
True. Execution repeats the checks after authorization before any effect.
The first atomic, fsynced intent occupies the existing negative marker path.
The unchanged historical PAM reader denies marker presence regardless of
payload schema, so a crash before a separate ownership journal exists remains
blocked. The marker then becomes the historical blocked marker while a separate
root-only operation journal retains the full ownership binding.

Publication reuses the historical root-only, bounded, NOFOLLOW, single-link
reader, stable per-UID lock, atomic writer and file/directory fsync. Operation
records have strict schema and duplicate-key rejection. Local phases advance
from intent (1), through legacy-blocked (2), to retired (3). Resume preserves
completed phases rather than regressing the legacy journal to blocked.

Resume requires fresh authorization, the same operation and inventory binding,
and unchanged storage state across the prompt. It never replaces another owner,
reconstructs a missing marker, or removes a proof recreated after retirement.
Completed retries are read-only. Inspection is read-only and corruption raises
an error rather than choosing ordinary admission. Success means only
`AdmissionWithdrawnNoQuiescence`; producers may still be active.

These are local revisions and hashes, not a global monotonic authority,
signature, anti-rollback protocol or protection from trusted root maintenance.
The journal does not yet own persistent system-unit masks or D-Bus retirements.
It does not implement the complete identity lifecycle or boot reconciliation.

## Validation

The marked Leap 16.1 VM verifies both test kernel markers and the disposable
disk serial. Existing ordinaryuser UID1002 is the target and installeduser
UID1000 is the peer. Both real user managers initially admit ordinary proofs
under SELinux Enforcing and the unchanged historical withdrawal PAM fixture.
The driver then stops the target manager before crash testing; this is not
producer revocation by `Operations`. Accounts, passwords and groups are unchanged.

Eight fresh child processes actually exit91 after these durable boundaries:

1. Intent marker publication.
2. Separate owned intent publication.
3. Historical blocked marker publication.
4. Historical blocked journal publication.
5. Owned legacy-blocked phase publication.
6. Positive proof unlink and directory fsync.
7. Historical retired journal publication.
8. Owned retired journal publication.

At each boundary a real systemd-user PAM attempt fails with status224/MainPID0
and the causal fixture rejection in a fresh journal cursor. The peer manager
PID remains unchanged. A different operation, denied authorization and a
changed inventory are refused without modifying proof state. Restoring the
catalog is an explicit trusted-root fixture step, not an operation API or an
anti-rollback claim. A newly constructed coordinator resumes with fresh
authorization, preserves the complete owner, retires the positive proof and
keeps the negative marker. Completed retries preserve storage and the peer
proof, inventory and manager. Final controls reject corrupt ownership,
recreated proof and missing marker, and verify read-only inspection.

The 22 new Python tests additionally cover authorization callback failures,
truthy non-True results, callback payload mutation, stale proof/plan, strict
schema and phase non-regression. Their storage doubles are decision tests,
not native enforcement qualification. The entire 455-test suite passed.

These crashes restart subprocesses and exercise real fsync; they do not restart
the kernel or emulate power loss. There is no qualified automatic boot recovery,
global revision authority, complete producer inventory, real Polkit transport,
NSS mutation, pending-auth coverage or production journal migration here.

Independent restoration verifies original PAM bytes/mode, vendor PAM and
passwd/group hashes; zero fixture UID processes, managers and sessions; removed
module, registry, proofs, inventory and linger; Permissive baseline; and SSH
disabled/inactive. Root evidence helpers/logs remain, so this is scoped cleanup,
not full filesystem rollback or complete kernel audit. No packages installed.

Verify archived evidence and captured source hashes offline:

```sh
python3 docs/evidence/parental-operation-journal/verify-evidence.py
```

Next: qualify recovery across a real VM reboot, then bind persistent producer
inhibitions to operation ownership. Global revision authority, complete
inventory/coverage, GDM paths, fictitious NSS lifecycle, product authorization
and release qualification remain separate gates.
