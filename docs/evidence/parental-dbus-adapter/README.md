# Experimental registered D-Bus activation adapter — 2026-10-02

24 native controls, 8 separate root-filesystem controls and 384 Python tests
passed (20 new decision tests). Issues #6/#102 remain OPEN, full parental
protection remains **NO-GO**. Local evidence only; no host, product PAM, recipe,
RPM, OBS or ISO changes. VM restored and powered off, QEMU exit 0.

`DBusActivation` verifies the immutable target withdrawal and a nonempty,
root-selected closed route catalog before authorization and again under the
per-UID shared lock. Inhibition retires exact definitions, calls native
`ReloadConfig`, and checks that every target name is absent from
`ListActivatableNames`. It does not infer that existing owners exited.
Revocation requires these fences and separate literal-True authorization,
stops only verified registered payload units, waits at most 25 seconds for
quiescence, then rechecks classification, catalog and admission. No shared
broker restart, account mutation, enrollment, reactivation or recovery API.

`RetiredRoutes` retains original root-owned definitions at non-activation
filenames in the same directory. Exclusive hard-link creation, directory
fsync, source unlink and another fsync keep conflicts from overwriting data.
An exact two-name intermediate can resume; a divergent record or unexpected
hardlink fails closed. The adapter never removes negative account authority
or restores retired routes. This is an experimental fixture mechanism, not a
proposal to remove arbitrary shared distribution services during enrollment.

## Native matrix

The disposable Leap 16.1 VM checks both dedicated kernel markers and disk
serial `lyra-admission-test`, and executes the main matrix in Enforcing mode.
Existing UID 1002 is the target, UID 1000 the peer. No accounts/groups are
created or changed. Six originally absent names form the reserved fixture
catalog: four target routes and two peer routes. Both `Exec+User` broker-created
transient units and `SystemdService` units have real libsystemd method replies
reporting UID/PID, verified against all four process UIDs, executable, cgroup
and native unit properties. These payloads have no PAM; the unchanged
historical withdrawal PAM guard separately fences the target user manager.

| Control | Native observation |
| --- | --- |
| Durable withdrawal plus logind termination | Both existing target D-Bus payloads survive; reproduces the gap |
| Denied inhibition; unknown or changed definition | No retirement, reload or stop |
| Authorized retirement and reload | Target names absent from activation list; old owners keep replying |
| Cold Exec and SystemdService routes | Calls denied with activation-specific errors |
| Denied revocation | Old process and persistent fences remain |
| Authorized scoped stop | Two pinned payload pidfds report exit; no target UID process or owner remains |
| Four reactivation attempts | Every retired target name rejects calls |
| Definition recreated externally with zero activity | Adapter refuses verification |
| Authorized retries | Retired records and negative account authority retained |
| Partial coordinator coverage | `UnsupportedProducer`; required producer set unchanged |
| Target user-manager admission | Status 224 and exact withdrawal PAM rejection; peer manager preserved |
| Peer services and shared bus | Original peer payload PIDs and broker PID 449 preserved throughout |

`retirement-controls.py` runs separately after restoration in Permissive mode
inside private root scratch. Eight controls cover idempotent inode-preserving
retirement, two-name intermediate resumption, conflicting destination,
unregistered hardlink, source symlink, writable directory, directory symlink
and path traversal. Scratch is removed. This does **not** qualify power loss.

Main native matrix passed on its first execution, actual detached child exit
0, empty stderr, cleanup exit 0. An initial Python decision-test harness run
failed because its shared setup lacked an `execute` helper; corrected before
native execution. The full final suite passed. Test doubles do not establish
native producer coverage.

## Evidence and restoration

`result.json`, raw stdout/stderr and `exit-status` retain the real execution.
`cleanup.json` and `routes-restored.json` record cleanup. Independent
`restore-check.py` and `restore-routes.py` verify PAM bytes/mode, vendor files,
account-file hashes, zero user processes/sessions/managers, no fixture bus
owners/activation names/paths, no fixture payload/cgroup leaks, original broker
PID, removed scratch, Permissive baseline and disabled/inactive SSH.
Root helper scripts, backups and logs remain; restoration is scoped, not a
full filesystem rollback. Complete kernel audit is not claimed.

Source/artifact hashes and native command IDs are in `provenance.json`.
Historical guard, writer, coordinator and manager-adapter sources are unchanged.
Verify offline:

```sh
python3 docs/evidence/parental-dbus-adapter/verify-evidence.py
```

## Remaining limits

This is a sequential, registered system-bus fixture on dbus-broker 36.
Pending activation races, arbitrary service discovery, duplicate names in
other search directories, aliases/drop-ins/generators, dbus-daemon variants,
session bus, untrusted-client policy, direct manual systemctl start and the
whole D-Bus namespace remain unqualified. Retired files require operation/
revision ownership and durable recovery integration before product use.
No reboot, crash injection, power loss, global monotonic authority, NSS role
mutation, Polkit/API or complete GDM session is qualified here. Root is trusted.

Next: implement and qualify the registered cron producer adapter; then complete
namespace inventory/authority, outstanding login coverage, global recovery and
account lifecycle. Adding scoped callback keys does not prove whole-account
protection, and unsupported coverage must remain a blocking result.
