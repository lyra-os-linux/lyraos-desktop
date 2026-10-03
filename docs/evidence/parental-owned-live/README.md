# Owned inhibitions with live scoped producers — 2026-10-03

57 native controls passed (29 system-unit controls and 28 D-Bus controls), both
on their first execution. The entire Python suite passed 496 tests, including
14 new integration decision tests. Issues #6/#102 remain OPEN and full parental
protection remains **NO-GO**. No host, product PAM, recipe, RPM, OBS or ISO
changes. Disposable VM independently restored between phases and powered off.

## Integration

The [filesystem ownership protocol](../parental-owned-inhibitions/README.md),
admission operation journal, inventory reader and original live producer
adapters are reused unchanged. `integration.py` supplies read-only
`CheckedMasks` and `CheckedRoutes` interfaces to those adapters. Each interface
captures an immutable target UID/operation/proof hash and exact resource list.
Every lookup validates the current complete owner, inventory binding, backend
and protocol versions, namespace and effect identity through a fresh owned
plan. Only fenced2 records are accepted. Unknown resources, changed route
digest or SystemdService binding, unprepared intent or divergent owner fail.

Prepare filesystem inhibitions with the existing owned gate and fresh
authorization before invoking the live adapter. The legacy `install`/`retire`
method names on the new interfaces perform checks only: they cannot create,
repair, unlink or authorize anything under an outer classification lock.
The original live adapter still verifies its closed catalog, requests its
authorization outside its classification lease, reloads the relevant upstream
component and verifies loaded masks/activation absence. Existing payloads are
revoked only after a separate explicit authorization and checked inhibition.
Filesystem ownership alone is never treated as stopped activity.

This is a trusted-root experimental factory, not an exported GUI/Polkit API or
production coordinator. Multiple fixture approvals deliberately exercise
separate filesystem and live-effect boundaries; no production approval UX or
capability protocol is inferred. Actual EX probes for inventory, target proof
and global ledger succeed inside every filesystem/live authorization callback,
showing these callbacks hold none of those locks. Read-only ownership checks
remain compatible with the adapter's outer proof SH lease.

## Native system units

The marked Leap16.1 VM requires both test kernel markers and disposable disk
serial. Existing UID1002 is the target and UID1000 the independent ordinary
peer; passwords, groups, identities and MAC mapping are unchanged. Real
managers initially admit ordinary proofs under Enforcing. Reserved vendor
units include target plain/guarded services and a service/timer pair, plus peer
plain and timer/service controls. Processes run in real system.slice cgroups.
Completed admission withdrawal and logind termination leave unguarded
producers alive, demonstrating why subsequent producer checks are necessary.

Inhibition denied before preparation has no mask or command effects. Unknown
units and changed source definitions fail before effects. Unprepared ownership
cannot cause automatic mask installation. Four masks are then prepared and
owned by the original negative operation with recorded source digests.
Changing the catalog inside live authorization invalidates the adapter before
daemon reload, retaining all masks and journals. The driver explicitly restores
the old fixture catalog for the subsequent positive case; this is trusted-root
maintenance, not an anti-rollback protocol or API repair.

The live adapter reloads systemd and checks all four loaded masks. Existing
payloads still run and scoped quiescence is false. Denied revocation leaves
them alive. Authorized revocation stops the timer before services and verifies
exited pidfds, empty registered cgroups and no target UID processes. All four
manual restarts fail as masked; no target reactivation occurs through the timer
window. The peer plain service and manager keep their PIDs and positive proof,
and the peer timer successfully restarts its own service.

A removed owned mask causes both quiescence and inhibition to fail without
recreation. Explicit root fixture restoration puts back the same original
symlink inode; no new ownership is silently adopted. Subsequent reload and
idempotent revocation preserve all ledger bytes/inodes. The whole coordinator
still refuses missing mandatory families and target manager PAM admission
remains denied with status224 and a causal fixture rejection.

## Native D-Bus

After independent restoration of the unit phase, the same VM starts separate
reserved system-bus fixtures: active target Exec/SystemdService routes, cold
target routes of both kinds, and independent active peer routes. User= payloads
run in actual system.slice units without PAM. The target admission operation
is withdrawn while these old payloads remain alive. Four route definitions are
retired under the owned protocol before invoking the live adapter.

Unprepared ownership, unknown route and changed definition are refused without
retirement/reload by the live adapter. Live authorization denied after ownership
keeps the prepared retirements intact. A catalog change during authorization
fails before reload. The successful adapter calls upstream ReloadConfig,
confirms the names are no longer activatable and demonstrates that old owners
remain alive. Cold routes cannot activate. Denied revocation preserves owners;
authorized stop binds existing payload PID, executable and cgroup, verifies
exited pidfds/no target owners or UID processes, and leaves peer owners,
ordinary manager/proof and shared broker PID448 unchanged.

All four target routes cannot reactivate after retirement. An externally
restored active definition is refused even with zero target processes. Retries
do not rewrite owner journals. The coordinator still refuses whole coverage
and PAM target admission stays blocked. The shared bus is never stopped or
restarted; fixture cleanup uses reloads and only reserved paths/payloads.

## Evidence, restoration and remaining gates

Both native matrices exit0 with empty stderr and cleanup0. Independent readers
verify original PAM bytes/mode, vendor PAM, passwd/group hashes, absent fixture
units/routes/module/proofs/registry/ledger/inventory/linger, zero relevant
processes/managers/runtime/sessions, Permissive baseline and disabled/inactive
SSH. Unit cgroups are empty, D-Bus fixture names are absent and broker PID is
preserved. No packages installed. Root evidence helpers/backups/logs remain;
this is scoped cleanup rather than whole filesystem rollback or kernel audit.

The new unit tests use declared memory storage/backends to check target and
resource binding, pending/completed states, read-only behavior, version/catalog
changes and refusal to repair. They are not native producer qualification.
Source and artifact hashes bind both native matrices and the full suite:

```sh
python3 docs/evidence/parental-owned-live/verify-evidence.py
```

These are two separate closed catalogs, not a simultaneous whole-account
transaction or exhaustive namespace inventory. Pending activations, races
between reload and stop, transport disconnects, ownership-ledger reboot,
power loss, global monotonic revision/anti-rollback, real NSS lifecycle,
GDM/pending-auth coverage, Polkit and production update/rollback remain
unqualified. Catalog revision rollback and mask restoration in the fixtures
are explicit trusted-root steps, never automatic recovery APIs.

Next: reboot the live owned resource ledger and revalidate fences/loaded
activation state with blocked recovery, then qualify pending activation races
and complete producer inventories before lifecycle and product integration.
