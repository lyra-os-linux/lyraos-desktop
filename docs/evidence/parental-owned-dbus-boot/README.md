# Owned D-Bus retirements across real reboots — 2026-10-03

51 native controls passed: 10 preparation, 22 first-boot and 19 failed-hook
second-boot controls. Two actual kernel reboots produced three distinct boot
IDs. All three matrices exited0 with empty stderr on their first execution.
The unchanged core's 496-test Python baseline from `parental-owned-live` is
reused and hash-bound; it was not rerun for this fixture-only change. Issues
#6/#102 remain OPEN and full parental protection remains **NO-GO**. No host,
product PAM, recipe, RPM, OBS or ISO changes.

## Persistent closed catalog

Historical admission ownership, inventory, filesystem retirement protocol,
read-only integration and D-Bus adapter are reused unchanged. Only the reserved
VM fixture moves its SystemdService units from runtime storage to persistent
`/usr/lib/systemd/system`. Six `org.lyra.OwnedBoot.*` service definitions,
a reserved compiled executable and root bus policy are newly installed on the
marked disposable Leap16.1 disk. Existing UID1002 is the target and UID1000
the independent ordinary peer. Passwords, groups, identities and MAC mappings
remain unchanged. No package installation or producer boot wants are needed;
activation is tested by actual system-bus method calls.

Before reboot, ordinary managers are admitted under Enforcing. Target and peer
Exec/SystemdService payloads activate in real system.slice cgroups with verified
UID, executable and PID. Target admission withdrawal and logind termination
leave the old unguarded D-Bus payloads alive. Three target routes reach fenced2.
A real child exits91 after retiring/fsyncing the fourth definition but before
committing its fenced journal. The fourth owner remains intent1 while its
physical definition is already absent from the activation filename. The live
adapter refuses the pending ownership set before authorization or reload.
These filesystem operations do not revoke the old live owners.

The crash boundary is **after the effect**. This does not show that pending
ownership without a physical retirement blocks activation. New brokers read
the durable absence of these four definitions; peer definitions remain active.
The VM-only boot hook sets Enforcing and inspects ownership without any
resume/authorization/repair call. It is ordered after local filesystems and
before dbus.service, logind and the user managers. The hook never queries the
bus. Direct kernel boot uses `enforcing=0` before this hook; initrd, early boot,
GDM, arbitrary ordering and production recovery configuration remain outside
this qualification. Before ordering does not imply a Requires failure barrier.

## First reboot

Admission proofs/journals, resource ledger and stable locks, inventory, registry
and roles, four retired definition hashes/inodes, peer definitions, persistent
vendor units, executable and policy survive byte-for-byte with inode identity.
The read-only hook observes three completed records and one pending record.
Target linger admission fails PAM with status224 and a causal fixture journal.
Ordinary peer linger admission succeeds. The new shared broker has this boot's
identity; the target routes are absent from ListActivatableNames and four real
activation requests fail ServiceUnknown/not activatable. Both peer routes
activate normally, including the persistent vendor SystemdService path.

Wrong operation and denied authorization leave all state unchanged. A root
fixture publishes catalog revision2; recovery refuses it before prompting.
Explicit root restoration republishes the old catalog bytes for positive cases
and changes only that catalog file's inode. This is not anti-rollback authority
or automatic owner repair. The pending record continues to refuse live reload.
Fresh authorization outside inventory/proof/global-ledger locks completes only
one owner journal, retaining the original retired inode. The live adapter checks
activation absence and scoped quiescence, calls upstream ReloadConfig and
preserves all owner records, peer payloads and this boot's broker process.

A root fixture temporarily adds an active filename as a hard link to an owned
retired definition. The facade refuses this divergent partial state as
ResourceChanged and neither retires it automatically nor rewrites its owner.
The root fixture explicitly removes the extra name and checks the original
retired inode. No activation attempt is made during this deliberately divergent
window: concurrent activation races remain unqualified.

## Second reboot with inspection failure

All four completed owners and retired definitions persist exactly. The boot
hook exits42 after Enforcing and before inspection. Target PAM admission and
all four D-Bus activations remain denied; ordinary peer admission and both peer
routes succeed. Wrong/denied operation and changed catalog still fail. Four
explicit fresh authorizations for completed resource retries preserve every
journal and inode. Upstream ReloadConfig preserves the broker and peer owners
within this boot. Each kernel reboot naturally creates a new broker/process
identity; no identical-PID-across-boots claim is made.

The final whole-account scope probe calls the historical coordinator's
read-only `_check` directly. It refuses missing mandatory families without
invoking the legacy resume or replacing its same-byte journal inode. All proof
and admission journal inodes therefore remain unchanged throughout both phases.
The trusted fixture's adapter has no postboot stop callback: old preboot payload
descriptors are never reused for revocation, and scoped empty activity after a
kernel reboot is not claimed as adapter-driven revocation.

## Evidence and restoration

```sh
python3 docs/evidence/parental-owned-dbus-boot/verify-evidence.py
```

Source/artifact hashes bind both boots, the crash91, read-only hook, failed
hook42, pending completion, completed retries, actual activation denials,
peer activations and broker preservation. Independent readers verify original
PAM bytes/mode, vendor PAM, passwd/group hashes, absent fixture service/retired
files/units/binary/policy/ledger/catalog/module/proofs/registry/roles/linger,
zero relevant processes/managers/runtime/sessions, Permissive baseline and
disabled/inactive SSH. The shared bus is never stopped or restarted by fixture
operations; it starts afresh as part of kernel reboot. Scoped cleanup uses
reloads and removes only originally absent reserved resources. All QEMU exits0;
the restored VM is powered off. Root helpers/backups/logs remain: not whole
filesystem rollback or a complete kernel audit.

This is a closed root-selected namespace, not exhaustive discovery, a coverage
issuer, whole-account transaction or production controller. Pending activation
and reload/stop races, transport disconnects, power loss, global monotonic
revision/anti-rollback, NSS lifecycle, GDM/pending-auth, Polkit, UI and production
update/rollback remain separate gates. Next: exercise pending activation and
concurrent reload/stop failures before complete inventories and lifecycle work.
