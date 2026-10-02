# Experimental registered cron adapter — 2026-10-02

19 final native controls and 404 Python tests passed (20 new decision tests).
Fixture-only ordinary account withdrawal for parental issues #6/#102. Full
parental protection remains **NO-GO**. No host, product PAM, recipe, RPM, OBS or
ISO changes; cron is installed temporarily in the disposable VM only.

`Cron` verifies a nonempty immutable job catalog and the already installed PAM
account route under the per-UID classification lock. `inhibit` verifies the
negative account authority persisted by withdrawal; it does not install a
fence after jobs have started, delete crontabs, or infer old jobs have exited.
Revocation requires a verified fence and separate literal-True authorization,
rechecks the target/catalog/route, signals only registered trusted payload
pidfds, waits at most 25 seconds for payload and root monitor exits and no
remaining target UID process, then rechecks admission. Partial failure retains
negative authority. No shared daemon restart, root monitor signal, role change,
proof restoration, enrollment or recovery API.

The experimental cron account module reuses the previous SSH ordinary account
check with its log message adapted to cron. It includes the unchanged
historical withdrawal guard. The requisite account control precedes the vendor
sufficient control; it validates positive ordinary proof, full NSS tuple,
per-UID classification gate and SELinux Enforcing. It denies marker/journal,
unknown/corrupt proofs and unsafe locks. Account management runs before MAC
session setup; this does not assert a pending session MAC label or authorize
supervised CLI. The cron fixture installs only the account control; historical
session guard is separately installed for the user-manager control.

## Native scope

The marked Leap 16.1 VM uses real minutely scheduling through cronie 1.7.2,
without changing the clock or accelerating cron. Existing ordinaryuser UID1002
is the target and installeduser UID1000 is the peer. No account/group/password
mutations. Each has a per-user crontab and a root `/etc/cron.d` entry executing
as that user, with a trusted C payload recording UID/PID/time then sleeping.
All four process UIDs, executable, native cron cgroup and job root monitor
ancestry are verified. Payload and root monitor pidfds are pinned before
withdrawal. Root is trusted; these jobs do not fork arbitrary command trees.

Cronie creates its user spool files owned by root, mode0600, rather than owned
by the named user. The fixture checks the actual root-protected files, exact
bytes/digest and filename-to-NSS binding. The closed root fixture catalog
refuses extra target system tables, changed definitions or a changed PAM route.
It is not automatic discovery of every cron producer or a product inventory.

Fixture proof/registry state is labeled with a temporary read/lock policy for
crond_t and init_t; no write permission is granted to cron. User crontabs use
restorecon under the VM's pre-existing fcontext rules, including historical
fixture customization. This is not qualification of stock ISO labeling.
The installed vendor crond PAM and shared common PAM files are preserved.

The matrix validates the baseline catalog positively before negative controls,
reproduces survival after withdrawal and logind, verifies denial of both target
routes at the next real minute with exact PAM rejection and native Cronie
account denial after a fresh journal cursor, and checks the peer schedules
continue. Authorized revocation stops only two pinned target payloads; two root
monitors exit naturally. Another real minute verifies target non-reactivation
while peer jobs continue. Loss of the guard with zero processes is refused;
retries retain negative authority. Target user-manager PAM denial is also
checked; the partial coordinator still returns UnsupportedProducer. Original
peer payload PIDs, peer manager/proof and shared daemon PID must survive the
entire transition. Daemon stop occurs only during final fixture cleanup.

## Preliminary failure

First native attempt failed after seven recorded controls because the fixture
incorrectly expected the user spool file owner to be UID1002. The native file
is root-owned. Its catalog rejection also masked the intended missing-PAM
negative test; those preliminary negative checks do not qualify their causes.
Cleanup passed. Exact failed source, raw output, status1, result and cleanup
are retained in `failed-attempt-1/`. A separate temporary crontab inspection
confirmed native uid0/gid0/mode0600/nlink1, and removed its file afterwards.
The corrected driver adds positive catalog/admission verification before
negative tests and repeats the complete matrix. The adapter's decision
algorithm and historical protocols are unchanged by this fixture correction.

## Reproduction, recovery and qualification limits

All guest helpers require root, both dedicated kernel markers and disk serial
lyra-admission-test. Only signed official cron4.2, cronie1.7.2 and debianutils5.4
RPMs are installed, with rpm --checksig. Before/after exact package name,
version, release and architecture sets must match after their removal. This
is not a full filesystem rollback: helper scripts, RPMs, backups and logs may
remain, and package scriptlet side effects are not exhaustively reversed.
Independent restoration checks PAM bytes/mode/vendor/shared files, account
hashes, no fixture tables/output/module/binary/policy/processes/sessions,
Permissive baseline, disabled/inactive SSH, stopped cron and removed packages.

Real waits are bounded180s per scheduling round, execution is detached from
the VM agent with raw logs and the actual child exit status. No scheduler
latency or complete kernel audit qualification. Pending fork/account races,
root jobs that later change users, non-PAM variants, arbitrary shell/descendant
trees, alternate cron implementations, whole cron namespace, global revision
and durable recovery, reboot/power loss, NSS lifecycle, product Polkit/API and
full GDM coverage remain pending. Root fixture authorization callbacks and
scoped catalogs are not production authority. Required producer keys stay
unchanged; scoped callbacks cannot establish whole-account coverage.

A second launch was refused before fixture setup because the previous run's
configuration checkpoint remained. This is an intentional baseline assertion,
not a producer verdict. `failed-attempt-2/` retains status1, empty stdout,
traceback, exact sources and startup metadata. Independent common restoration
passed, then idempotent cleanup with `--reset` removed only the retained
checkpoint/original PAM backup. The complete matrix was launched afresh.


Final complete native run passed, actual child exit0, empty stderr, cleanup0.
Original daemon PID1241 and peer jobs survived the whole matrix. Independent
restoration and exact RPM tuple restoration passed. VM powered off, QEMU exit0.
Sources and artifacts, including both unsuccessful attempts, are hashed in
provenance.json. No negative controls from the failed matrix are promoted into
final qualification. Verify offline:

```sh
python3 docs/evidence/parental-cron-adapter/verify-evidence.py
```

Next work: establish authoritative producer inventory/coverage and durable
operation ownership/recovery across these scoped adapters, then qualify pending
login/GDM/account lifecycle and product authorization/release gates. All seven
producer families have some fixture work, but this does not qualify all seven
namespaces or authorize real account enrollment.
