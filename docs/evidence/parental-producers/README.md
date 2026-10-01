# Experimental system services and timers — 2026-10-01

Native disposable Leap 16.1 VM evidence for parental issues #6/#102. No host, product PAM, recipe, OBS or ISO changes. Full parental protection remains **NO-GO**.

## Result

14 native assertions and 270 existing Python tests passed. Three assertions deliberately reproduce gaps; passing this matrix does not mean those gaps are fixed.

- Root-owned system services with `User=producerfixture` and no `PAMName` execute after the durable generation barrier. Timer-triggered services do the same.
- `loginctl terminate-user` does not terminate these unguarded producers in `system.slice`. Their PIDs survive unchanged.
- The experimental PAM binding rejects new guarded services and timer executions with systemd status 224 and the exact guard rejection in their journals. A live guarded producer holds the old-generation lease.
- Explicitly stopping only registered fixture units and timer triggers releases the lease and preserves the ordinary account's service. This is an experiment with a known unit list, not a general producer discovery or revocation implementation.
- After explicit reenrollment, the stale PAM binding is denied; updating its generation admits the guarded service and timer.

The baseline payload is `sleep`, under normal account mapping. This experiment does not prove supervised MAC confinement or authorize supervised CLI execution in the product.

## Reproduction and provenance

`exercise.py` refuses any machine lacking both test boot markers and the dedicated disk serial. It creates temporary accounts, PAM and SELinux fixtures, executes the matrix in Enforcing mode, then restores Permissive mode and removes its fixtures. `restore-check.py` independently inspects removal; `verify-evidence.py` verifies archived hashes and assertions offline.

Run the verifier with `python3 docs/evidence/parental-producers/verify-evidence.py`. Native source hashes are in `result.json`; execution IDs, artifact hashes and VM termination are in `provenance.json`.

Three preparatory harness runs failed on transient unit timing/garbage collection. `Type=exec` and handling discarded units/timers corrected observation and cleanup; the final entire matrix and independent restoration passed. One failed cleanup required an explicit fixture-only cleanup before the final run. These were harness corrections, not product fixes.

## Remaining qualification

Cron/cronie is absent in this VM: no native cron result is claimed. Inventory package-name failure for `dbus-1-broker` does not mean the system bus is absent; the inventory records an active D-Bus broker service. D-Bus activation has not been exercised here. Inventory describes this VM, not a candidate ISO. Complete kernel audit, power-loss qualification, real account lifecycle, producer inventory/revocation authority, recovery, Vega/Polkit integration and release gates remain pending.
