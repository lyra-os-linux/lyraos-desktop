# Experimental system-bus D-Bus activation — 2026-10-01

Disposable Leap 16.1 VM evidence for parental issues #6/#102. Full account protection remains **NO-GO**. No host, product PAM, recipe, OBS or ISO changes.

## Native result

17 assertions and 270 existing Python tests passed. Four assertions reproduce known protection gaps, rather than fixes.

| Path | Observed result |
| --- | --- |
| `SystemdService=` with experimental `PAMName=` | Baseline admitted; new blocked or stale-generation activation rejected, status 224 and exact PAM account rejection |
| `SystemdService=` without PAM | New activation succeeds after durable barrier; survives `loginctl terminate-user` |
| Only `Exec=` and `User=` | Installed dbus-broker 36 creates a transient systemd unit with numeric User=31200 and no PAM; new activation succeeds after barrier and survives logind |
| Already owned names | Existing guarded and unguarded services continue answering real method calls after barrier |
| Ordinary account | Original service PID and replies survive the entire transition |

The payload returns its UID and PID through an actual D-Bus method. The harness also verifies all four process UIDs, trusted executable, unit identity and process cgroup. Vendor PAM moves guarded payloads to a logind user session; unguarded payloads remain under system.slice, including broker-created transient units.

A live guarded producer retains the old-generation lease. The barrier denies future PAM admissions; it does not revoke existing D-Bus owners. The fixture then removes only the target's known activation definitions and calls native ReloadConfig before stopping only its known systemd units. Four unique live payload pidfds become readable after stop. Target names lose owners, the removed plain route cannot reactivate, and the lease allows tombstone/explicit enrollment. Stale PAM generation is denied; updated generation recovers the guarded baseline.

The shared D-Bus service MainPID remains 449 and the ordinary payload connection keeps answering. No shared bus restart or bespoke process signal is used. Independent restoration verifies fixture definitions, policy, binary, PAM, SELinux policy, registry, accounts and processes are removed, with no sessions and the standard sshd still disabled/inactive. The VM is powered off, QEMU rc0.

## Reproduction and evidence

`exercise.py` refuses machines lacking both dedicated boot markers or the disposable disk serial. It uses the unchanged experimental guard/CIL from `../parental-producers/` and V2 writer from `../parental-registry-barrier/`, not a production control. `service.c` compiles with libsystemd. Root creates fixture accounts, definitions and temporary PAM/policy, executes in Enforcing mode, then restores Permissive and removes the fixtures in finally.

`restore-check.py` is an independent read-only inspection for this run (expected shared-service PID 449). `verify-evidence.py` checks source/artifact hashes and the archived assertions offline. `provenance.json` records execution IDs and SHA-256 values. Run:

```sh
python3 docs/evidence/parental-dbus-system-activation/verify-evidence.py
```

Two initial harness runs corrected assumptions about the PAM session cgroup and broker-generated numeric User property. Both restored their fixtures; the final complete native run and independent restoration passed. The final denial units were not exercised in those preliminary runs; their two archived rejection lines belong to the final matrix.

The observed broker delegation also matches the [upstream launcher documentation](https://github.com/bus1/dbus-broker/blob/main/docs/dbus-broker-launch.rst); activation file semantics are in the [D-Bus specification](https://dbus.freedesktop.org/doc/dbus-specification.html).

## Qualification limits and next work

This is sequential, fixture-only, system-bus activation on dbus-broker 36. It does not qualify pending activation races, arbitrary real services, discovery of all producer units, dbus-daemon variants, hot enrollment, reboot/crash recovery or complete kernel audit. Root callers intentionally isolate producer admission from client authorization; untrusted-client access policy is not qualified here. Baseline mapping is normal/unconfined, not parental MAC confinement or product permission for supervised CLI.

Removing known fixture activation files is an experimental disarm, not a product architecture: generic/shared services cannot simply be removed during account transition. General account quiescence, durable producer inhibition and revocation authority need the lifecycle ADR and upstream integration. Session-bus work has separate evidence under parental-activation and is not requalified here. Cron/cronie is absent in the VM and remains unqualified; logout/boot/lingering, real account lifecycle, backend, Vega/Polkit, privacy and release gates also remain pending.
