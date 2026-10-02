# Experimental inventory preflight — 2026-10-02

23 native inventory/storage/preflight controls and 433 Python tests passed
(29 new decision/schema tests). Issues #6/#102 remain OPEN, full parental
protection remains **NO-GO**. No host, product PAM, recipe, RPM, OBS or ISO
changes. Disposable VM restored and powered off, QEMU exit0.

## Behavior

`Inventory` reads a bounded root-only per-UID manifest under a stable root-only
shared lock. It rejects symlinks, hardlinks, permissive directories/files,
missing locks, duplicate JSON keys, ambiguous schema/identity, unknown families
and missing mandatory families. Every manifest contains the unchanged seven
REQUIRED keys. Each family is explicitly `registered` or `unsupported`, with
an adapter source digest and immutable route identifiers/digests. `registered`
requires a nonempty catalog. No `complete` status is accepted: a configuration
field cannot issue a certificate of whole-namespace coverage. Unknown absence
is not ordinary classification and zero activity is not coverage evidence.

`InventoryGate` is a separate wrapper around the unchanged ordinary withdrawal
coordinator. Its default `whole-account` factory policy refuses both partial
catalogs and a manifest naming all seven families as registered, before asking
for authorization or beginning withdrawal. A complete coverage issuer has
**not** been implemented. No success path authorizes real account activation.

The explicit `registered-test` policy is only a trusted experimental factory
choice, never a GUI/API selector. Its plan binds the inner withdrawal plan
(UID, operation, proof hash and proof snapshot), full inventory identity,
revision/digest, routes, and exact adapter objects plus current source digests.
It requires every mandatory binding and a literal-True root route verifier.
Changing an adapter implementation, its object, route descriptor, identity or
inventory snapshot invalidates the plan. The underlying withdrawal plan is
also rechecked before authorization and after it, before effects.

Authorization holds no inventory lock. Once authorized, the per-UID shared
inventory lock covers effects; cooperating publishers require the same stable
exclusive lock. Another UID has an independent lock. Checked adapter proxies
verify the inventory/bindings before and after every callback, with a
context-local active plan and exact target UID/operation/proof hash. They
cannot execute outside this context. A post-withdrawal change stops remaining
callbacks and retains negative authority. The resulting string is only
`CheckedWithinRegisteredInventory`. There is no publish/enroll/unblock or
unqualified recovery/resume API.

The revision is a local catalog value combined with a snapshot digest, **not**
a global monotonic authority or anti-rollback protocol. External root remains
trusted maintenance; root can restore prior bytes/revision. The fixture
publisher is an explicit root test helper, not an inventory discovery service
or a production writer protocol. It does not automatically increment revisions.

## Native controls and scope

The marked Leap 16.1 VM verifies both dedicated kernel markers and disk serial
lyra-admission-test. Existing ordinaryuser UID1002 and installeduser UID1000
have positive proofs and real user managers admitted by the unchanged
withdrawal guard in Enforcing mode. No account, group or password mutations.
Only classification and user-manager have real bound adapters in this matrix;
other five families are explicitly unsupported. No fake True callbacks for
missing families are installed. Earlier producer fixtures are not re-run here.

The native matrix checks:

- root-protected inventory decoding with five unsupported families;
- default whole-account refusal and refusal of a manufactured seven-name
  registered claim, without invoking producer adapters or authorization;
- a deliberately constructed candidate (not an issued whole-coverage plan)
  cannot bypass the default gate;
- stale revision and changed route digest without a revision bump are rejected;
- divergent full NSS tuple, `complete` claim, missing family and unknown extra
  family are rejected;
- group-readable file/directory, hardlink, symlink, oversized file, duplicate
  JSON key and missing stable lock are rejected;
- an exclusive target lock returns Busy while the peer inventory remains
  readable, and a cooperating writer cannot replace a shared-lock snapshot;
- every preflight refusal preserves target/peer manager PIDs and positive proof
  state, with zero authorization/adapter calls;
- an existing withdrawal marker/journal is never removed by inventory refusal.

The last negative-authority control explicitly invokes the already-qualified
fixture withdrawal writer; it is not whole-account admission through this
gate. There are no native successful registered-test transitions across all
seven producer families in this stage. Such successes in the decision tests
use declared synthetic adapters and are not producer qualification.

The final native matrix passed on its first execution, actual detached child
exit0, empty stderr, cleanup0. Preliminary Python-only harness failures came
from a fake lock attribute shadowing its method and module-loader leakage;
corrected in the new test harness, leaving historical sources/tests unchanged.
The final entire suite passed. All captured source/artifact hashes are in
provenance.json. Verify offline:

```sh
python3 docs/evidence/parental-inventory-gate/verify-evidence.py
```

## Restoration and remaining work

Independent common restoration verifies original PAM bytes/mode, vendor PAM,
passwd/group hashes, zero fixture UID processes/managers/sessions, removed
registry/proofs/module/linger, Permissive baseline and disabled/inactive SSH.
Independent inventory inspection verifies the entire fixture authority directory
and locks are absent. Scoped restoration leaves root helpers/backups/logs; it
is not a complete filesystem rollback or kernel audit. No packages installed.

Whole-machine producer discovery, namespace completeness, qualification of
route verifiers, complete coverage certificates, signed/durable operation
ownership, global monotonic revision, idempotent recovery, crash/reboot/power
loss and real API/Polkit are pending. Per-UID lock independence is demonstrated;
whole service concurrency and asynchronous inventory producers are not.
The registered-test plan is a process-local prototype, not a durable operation
record. Route identifiers/digests are root catalog metadata, not a discovery of
all apps, shell descendants, GDM paths or privileged user-switching producers.

Next: operation ownership and durable journal/revision/recovery gates, then
complete producer inventories and remaining GDM/pending-auth coverage before
NSS lifecycle and product authorization/release qualification. Do not convert
seven scoped adapter keys into whole-account authority.
