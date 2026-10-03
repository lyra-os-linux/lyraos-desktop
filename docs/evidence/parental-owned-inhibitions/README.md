# Experimental ownership of persistent filesystem inhibitions — 2026-10-03

36 final native controls and 482 Python tests passed (27 new decision/schema
tests). Two earlier native attempts are archived, including their failures and
independent baseline/restoration checks. Issues #6/#102 remain OPEN and full
parental protection remains **NO-GO**. No host, product PAM, recipe, RPM, OBS or
ISO changes. Disposable VM independently restored and powered off.

## Ownership protocol

`OwnedInhibitions` adds a root-only resource ledger to the existing completed
negative admission operation. The owner must already be retired with its
negative marker and historical journal intact. Every resource is selected from
an immutable trusted-root factory mapping; its name/digest and current backend
source hash must match a registered route in the owner's exact inventory.
There is no client-provided arbitrary path, unmask, restore-route, enrollment
or unblock API. These are scoped filesystem records, not whole-account coverage.

Each record binds the complete admission owner (identity, operation, original
proof hash/snapshot, inventory revision/digest), family/name/route digest,
backend source digest, ownership protocol source digest, namespace device/inode,
original D-Bus definition device/inode/digest, and final effect identity.
Schema and JSON keys are strict. The historical root-only bounded reader,
atomic writer and file/directory fsync are reused for ledger publication.

A stable precreated `.gate-1.lock` in the dedicated ledger serializes cooperating
resource writers across target UIDs. The number 1 is an internal global lock
slot, not a target account. It is never created by a reader. One configured
namespace per producer family belongs to this ledger; the key hashes family
and resource name. A replacement namespace conflicts with an existing record
rather than creating another owner. Shared resources cannot have multiple
owners; no reference-counting policy is inferred.

Lock order is inventory SH, negative proof SH, global ledger SH/EX. Short
filesystem effects use EX only for the global ledger; there is no recursive
per-UID EX upgrade or session lifetime lock. Nested proof SH is compatible with
historical classification readers. Unrelated resources currently share the
same short global ledger lock and can receive Busy; service-wide concurrency
and asynchronous/uncooperative writers are not qualified.

Planning checks owner, inventory, versions, namespace and resource state.
Authorization receives a detached record and must return literal True outside
the layer's locks. Execution rechecks the exact plan after the prompt. Intent1
is fsynced before the filesystem effect; fenced2 is published only after
checking the effect identity. Completed retries are read-only and still require
fresh authorization. Inspection is read-only. Success means only
`OwnedFilesystemInhibitionNoQuiescence`, not loaded systemd/bus inhibition.

An existing mask or retired/partial D-Bus route with no matching ledger owner
is never adopted. A different owner, changed catalog/version/namespace, corrupt
record, removed completed mask or replaced inode requires recovery. The layer
never removes a fence or silently recreates a missing completed one. Pending
intent may finish an already created matching effect; trusted root could make
an indistinguishable effect during that crash window. This is not protection
against root maintenance or a causal proof of external administrators' actions.

The backend operations use pinned, validated directory descriptors. Masks use
exclusive symlink creation and directory fsync. Routes reuse the historical
definition/partial-state validation and perform exclusive hard-link publication,
fsync, unlink and fsync on the pinned descriptor. Original definition inode and
digest are preserved through retirement and partial recovery. Historical source
files and earlier evidence remain unchanged.

## Validation and failures

The marked Leap 16.1 VM requires both test kernel markers and disposable disk
serial. Existing target UID1002 and peer UID1000 initially admit real ordinary
managers under Enforcing. The driver stops the target manager and completes
negative admission withdrawal before resource effects; this is not revocation
by this layer. Root-private scratch directories hold real masks and real
D-Bus definition bytes. No scratch route is registered with the live broker,
and no scratch mask is loaded as an installed system service.

For each family, three child processes actually exit91 after intent fsync,
effect fsync, and fenced-journal fsync. At every boundary a real target PAM
admission fails224 with the causal fixture rejection. Fresh authorization
resumes the same owner, and completed retries preserve ledger bytes/inodes.
The peer positive proof, catalog and manager PID remain unchanged through
these controls. A separately constructed real hard-link intermediate after a
durable intent resumes without recreating the active source or changing inode.
This intermediate is an explicit fixture step, not a process crash at the
internal link boundary.

Other native controls reject unowned masks/retirements, wrong operation,
truthy authorization, changed inventory, lost/corrupt ownership, removed or
replaced completed masks, replaced retired definitions, missing stable ledger
lock and group-readable records. Proof SH nesting is demonstrated. Finally a
second real negative admission operation is deliberately created for UID1000
to test cross-UID resource collision; it cannot claim UID1002's fence or prompt
for permission. The existing peer manager remains active. The global lock
returns Busy to both UIDs. This deliberate final withdrawal is not accidental
peer damage and does not establish revocation or future peer admission.

Attempt1 failed before setup because `owned-common.py` was imported as
`owned_common`. The original baseline was independently verified. Attempt2
passed 30 controls, then exposed misattribution of a missing ledger lock:
the inner OSError crossed the historical inventory context manager and became
UnknownInventory. Cleanup and independent restoration passed. The new layer
now normalizes inner OSError to StorageFailure before leaving that context;
two regression tests cover ledger and backend errors. Historical inventory
code is unchanged. Final matrix exit0, empty stderr, cleanup0; suite482 PASS.

## Boundaries and next gate

Ownership has not yet been integrated into live SystemUnits/DBusActivation
adapters, daemon reloads, pending bus activation, stop/revocation or reboot of
these new resource records. The previous admission-owner reboot gate does not
qualify this ledger. No global monotonic revision, signature, anti-rollback,
power-loss, complete inventory, NSS lifecycle, Polkit or product migration.

Independent readers verify original PAM bytes/mode, vendor PAM, passwd/group,
zero fixture UID processes/managers/runtime/sessions, removed fixture module,
registry, proofs, catalog, ledger/masks/routes scratch and linger, Permissive
baseline, and disabled/inactive SSH. No packages installed. Evidence helpers,
backups and logs remain; scoped cleanup is not full rollback or kernel audit.

```sh
python3 docs/evidence/parental-owned-inhibitions/verify-evidence.py
```

Next: connect verified owned fences to the scoped live producer adapters and
qualify reload/inhibition/revocation plus restart/reboot recovery. Keep
authorization outside any outer classification lock; a read-only ownership
check inside it must not become an implicit mutation or approval shortcut.
