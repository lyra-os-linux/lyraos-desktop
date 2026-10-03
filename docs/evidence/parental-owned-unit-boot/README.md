# Owned system-unit barriers across real reboots — 2026-10-03

43 native controls passed: 6 preparation, 20 first-boot and 17 failed-hook
second-boot controls. Two real kernel reboots produced three distinct boot IDs.
All three matrices exited0 with empty stderr on their first execution. The
unchanged core's 496-test Python baseline from `parental-owned-live` is reused
and hash-bound; it was not rerun for this fixture-only change. Issues #6/#102
remain OPEN and full parental protection remains **NO-GO**. No host, product
PAM, recipe, RPM, OBS or ISO changes.

## What this qualifies

The historical admission journal, inventory, filesystem ownership protocol,
read-only live integration and system-unit adapter are reused unchanged.
The marked disposable Leap16.1 VM uses existing target UID1002 and ordinary
peer UID1000, without identity, password, group or MAC mapping changes.
Root-selected fixtures install reserved vendor services and timer/service
pairs in `/usr/lib/systemd/system`; exact boot wants are explicit root fixture
setup. These are persistent files, unlike the preceding D-Bus fixture's runtime
units. Ordinary user managers and actual system.slice payloads run under
Enforcing before withdrawing target admission.

Three target masks reach fenced2. A real child exits91 after applying/fsyncing
the fourth mask and before committing its fenced journal. The timer record
remains intent1 although its physical mask exists. Old unguarded processes
remain alive before reboot: filesystem inhibition is not process revocation.
The live adapter refuses the incomplete ownership set without reload or
journal completion. This crash boundary is **after the physical effect**, not
before it; no claim that a missing effect would block an unguarded boot unit.

A VM-only boot hook runs after local filesystems and before logind, the user
managers and reserved boot producers. It applies Enforcing and reads admission
and resource ownership; it has no authorization/resume/repair path. The direct
kernel boot uses `enforcing=0` before this hook. This does not qualify initrd,
early boot, arbitrary ordering, GDM, or production recovery configuration.
The fixture hook is not coupled with Requires to producer units: the second
boot deliberately demonstrates continued physical mask enforcement when the
hook fails after applying Enforcing and before inspecting ownership.

## First reboot

Proofs, admission journals, inventory bytes and inode identities, stable locks,
resource ledger, registry/roles, vendor definitions and all mask inodes survive
unchanged. The hook observes the same three fenced and one pending records and
writes only its evidence file. Target linger auto-admission fails PAM with
status224 and a causal fixture journal entry. Ordinary peer linger admission,
plain service and timer/service pair start normally in this new kernel boot.
All four target units are loaded as masked with no processes; explicit start
attempts fail as masked.

Wrong operation and denied resource authorization preserve the entire state.
A root fixture changes the catalog revision and recovery is refused before
prompting. The fixture explicitly publishes the old catalog bytes again for
subsequent positive cases. Atomic publication changes that catalog file's
inode; this is not anti-rollback authority or an API that repairs a stale owner.
The existing content binding is revalidated by the unchanged protocol.

Pending ownership still refuses live inhibition after boot. A fresh resource
authorization, verified outside inventory/proof/ledger locks, completes only
one journal; mask inodes, other ledger entries, proofs and catalog remain
unchanged. The live adapter verifies loaded masks, scoped quiescence and
upstream daemon-reload without rewriting ownership. Temporarily renaming one
mask causes ResourceChanged with no automatic recreation or live command.
An explicit root fixture restores the same original mask inode. The peer timer
can reactivate its service while the target remains fenced.

## Second reboot with recovery failure

All four completed records and physical masks survive unchanged. The boot hook
exits42 after setting Enforcing, before any inspection. Target auto-admission
and all unit starts remain denied; peer manager and producers start normally.
Wrong/denied operation and changed catalog remain refused. Four explicit fresh
authorizations for completed retries leave every resource journal and inode
unchanged. Loaded-mask checks and daemon-reload preserve owner state; peer
service/timer activity remains independent. Peer PIDs naturally change across
kernel reboots; preservation checks compare PIDs within each boot and durable
ordinary proof/catalog bindings across boots.

The separate end-of-phase whole-coordinator probe uses the historical legacy
withdrawal resume before refusing missing producer families. That authorized
probe atomically replaces the legacy `.withdrawal-1002.json` inode with the
same bytes; it is not a read-only legacy retry. It does not alter resource owner
journals, proof authority or masks. The next boot snapshot includes this
explicit probe's result. Read-only claims here apply to the boot hook, owned
resource retries and live reload checks, not that historical coordinator call.

## Evidence and restoration

```sh
python3 docs/evidence/parental-owned-unit-boot/verify-evidence.py
```

The verifier binds executed source hashes to the historical dependencies,
asserts three boot IDs, pending/completed transitions, physical inode retention,
strict read-only hook/retries, target denials and peer behavior. Separate
readers verify original PAM bytes/mode, vendor PAM, passwd/group hashes, absent
reserved units/boot wants/ledger/catalog/module/proofs/registry/linger, empty
relevant cgroups/processes/managers/sessions/runtime, Permissive baseline and
disabled/inactive SSH. The VM is powered off; all QEMU exits0. No packages
installed. Root evidence helpers/backups/logs remain: scoped restoration, not
whole filesystem rollback or complete kernel audit.

This is a trusted-root closed unit catalog experiment, not a whole-account
transaction, exhaustive namespace inventory, coverage issuer or production
controller. Whole protection remains refused. D-Bus route ownership across
reboot is still unqualified. Pending activation/reload-stop races, transport
failure, power loss, global monotonic authority/anti-rollback, NSS lifecycle,
GDM/pending-auth, Polkit, UI and product update/rollback remain separate gates.
Next: persistent D-Bus fixtures and route ownership across actual reboots,
then producer races and complete inventories.
