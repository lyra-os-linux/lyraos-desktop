# Experimental native cron admission and revocation — 2026-10-01

Disposable Leap 16.1 VM evidence for parental issues #6/#102. Full account protection remains **NO-GO**. No host, product PAM, recipe, OBS or ISO changes.

## Native result

9 checks and 270 existing Python tests passed. One check reproduces a revocation gap. This does not complete parental protection.

Real minutely jobs run through the installed openSUSE cronie 1.7.2, both per-user crontabs and root-owned `/etc/cron.d` entries that execute as the test user. The experiment preserves the vendor PAM stack, prepending an experimental requisite account guard before its sufficient account control. Native policy and PAM configuration are archived in inventory.json.

- Initial user/system jobs for both accounts execute with verified process UIDs and trusted payload binary.
- Two root cron monitors retain the supervised generation lease while the payloads run. Transition returns Busy and keeps the durable barrier.
- On the next real minute, the supervised user's two routes are denied. The archive records two exact guard rejections and two native cron account denials after a fresh journal cursor; output files have no extra supervised execution. Ordinary jobs continue.
- `loginctl terminate-user` reports the user is not logged in or lingering; the already running cron payloads survive in system.slice. This is the reproduced gap, consistent with this VM's common-session-nonlogin stack having no pam_systemd.
- Only two known fixture payloads, each with verified UID 31300 and executable, receive SIGTERM through pidfds. Their pidfds report exit; the root cron monitors close their leases naturally. No root monitor or shared daemon receives a custom signal. Ordinary original jobs remain alive.
- After explicit tombstone/enrollment, the old PAM generation is rejected on both routes in another minute (two more exact account denials). Updating the generation admits both new supervised jobs.
- Original ordinary payload PIDs and daemon PID 1252 remain unchanged throughout the transition. The daemon is stopped only for final fixture cleanup.

The payload records UID/PID/epoch and sleeps to keep jobs alive; it does not fork, daemonize or perform privileged work. Baseline execution uses normal SELinux mapping and is not parental MAC confinement or product permission for supervised CLI.

## Reproduction and provenance

The VM originally had no cron. Official Leap 16.1 RPMs for cron 4.2, cronie 1.7.2 and debianutils 5.4 were downloaded on the host after guest DNS failed, copied into the disposable VM and passed native `rpm --checksig` with signatures OK. Installation was restricted to these three new packages. No recipe/package publication was performed.

`exercise.py` requires root, both dedicated boot markers and disk serial lyra-admission-test. It reuses the unchanged guard from ../parental-producers and writer V2 from ../parental-registry-barrier, installs temporary read-only registry access for crond_t, and executes in Enforcing mode. The fixture's crontabs receive restorecon according to the VM's pre-existing fcontext rules, without changing those rules. Those rules include earlier fixture customization: they are not proof of stock ISO labeling. Initial cron_spool_t changed to user_cron_spool_t; native admission was exercised after this preparation.

The VM command agent imposes a 120-second limit. `launch.py` runs the long experiment detached with explicit stdout/stderr files; `capture.py` independently verifies the finished process, complete checkpoint output and result hash. Four real scheduling rounds are used; no clock change or accelerated daemon is used. Each scheduling wait is bounded at 180 seconds; this is not a scheduler latency qualification.

`restore-packages.py` checks that only cron/cronie/debianutils were introduced, verifies removal dependencies, disables the installation's auto-enabled unit, removes exactly these three RPMs, and checks the original package **name set**. This does not claim a bit-identical filesystem or verification of every installed package version. `restore-check.py` independently checks no fixture processes/sessions/accounts/groups/homes/tables/PAM/module/registry/policy remain and that the shared original PAM files are preserved. Standard sshd remains disabled/inactive; VM returns to Permissive and is powered off, QEMU rc0.

Run the offline verifier:

```sh
python3 docs/evidence/parental-cron/verify-evidence.py
```

provenance.json binds native execution IDs, sources, downloads and artifacts by SHA-256. The current result is separate from preliminary failures:

1. Initial root-created user crontabs had an incompatible spool type, so only system jobs ran. Cleanup signaled the test payloads but its single poll returned before every pidfd was readable; this observation helper was corrected to accumulate exits.
2. The next foreground experiment hit the agent's 120-second cap. It had no final verdict and required explicit fixture cleanup; interrupted-cleanup.py records the successful idempotent cleanup version.
3. A temporary systemd launcher failed to observe initial output within its 90-second wait. Its complete fixture cleanup passed; this timing/launcher observation is unresolved, not declared a product fix. preliminary-unit-result.json preserves the failure.
4. The final detached execution with explicit logs, corrected spool preparation and a 180-second wait passed every native assertion and cleanup check.

The upstream [security.c](https://github.com/cronie-crond/cronie/blob/cronie-1.7.2/src/security.c) shows the non-root job PAM account/session flow; [cron.8](https://github.com/cronie-crond/cronie/blob/cronie-1.7.2/man/cron.8) documents PAM access control. Installed native configuration and execution, rather than current upstream master, determine the result here.

## Consolidated producer findings

| Producer | Experimental admission | Existing execution revocation | Remaining product work |
| --- | --- | --- | --- |
| SSH with PAM | Generation barrier denies new account admission | Native logind revokes registered sessions/transports, including root monitors | SSH variants, hot enrollment, account-wide producer inventory |
| System services/timers | PAMName guard denies; no-PAM User= bypasses | Explicit fixture units; logind misses unguarded units | Durable inhibition and inventory of real units |
| System-bus D-Bus | Guarded SystemdService denies; unguarded and broker Exec+User bypass | Disarm known fixture routes before stopping units | Shared/generic service policy, pending activation races, real producer discovery |
| Cron non-root user/system entries | PAM guard denies both routes | Trusted fixture payload pidfds release root monitor leases; logind misses jobs | Real command/descendant coverage, scheduling inhibition, crash/recovery integration |

These experiments do not authorize identity mutation or establish quiescence of arbitrary accounts. A trusted payload list is not a general process discovery/revocation service. Root cron commands that later switch users, arbitrary shell trees, variants without PAM, pending fork/admission races, logout/boot/lingering, complete audit, real NSS account lifecycle, recovery authority, backend/Vega/Polkit, privacy and release gates remain pending. Cron was absent in the initial VM; qualification does not implicitly add it to the product or qualify an exact ISO.
