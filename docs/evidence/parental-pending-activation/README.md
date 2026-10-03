# Pending D-Bus activation and explicit failures — 2026-10-03

28 native controls passed on the first execution, with nativeexit0, empty
stderr and cleanup0. The unchanged core's 496-test Python baseline is reused
and hash-bound, not rerun for fixture-only code/documentation. #6/#102 remain
OPEN and full parental protection remains NO-GO. No host, product PAM, recipe,
RPM, OBS or ISO changes. The disposable VM is independently restored and off.

## Actual requests and payloads

The existing admission owner, inventory, resource ownership, read-only
integration and DBusActivation adapter are reused unchanged. New reserved
`org.lyra.PendingActivation.*` fixtures use the same ordinary accounts and
system bus. Passwords, identities, groups and MAC mapping are unchanged.
Two actual busctl clients initiate TargetUnit/SystemdService and TargetExec
requests. The new VM-only C fixture stops itself with SIGSTOP before connecting
to the bus or acquiring its name. Both clients are pending, both names have no
owner, and actual UID1002 payloads exist in verified system.slice cgroups.
The controller captures executable/argv/UID/cgroup/MainPID and pins both with
pidfds. This is an actual pending activation, not a cold definition or fake
callback result. Peer Exec/SystemdService owners activate normally.

Admission withdrawal and logind termination leave both pending producers alive.
Four filesystem route retirements are then owned and committed, with every
fixture authorization verifying that inventory/proof/global-ledger EX locks
are available. Live inhibition denied leaves the negative state intact. A real
ReloadConfig command to an absent local socket fails and the adapter refuses
success while retaining retirements and old payloads. The subsequent actual
ReloadConfig removes target activatable names but does not prove quiescence.
Cold target activations fail; the two previously started producers still exist.

The controller releases the verified SystemdService payload using its pidfd;
it acquires its name after route retirement and serves a Probe. Revocation
denied leaves it and the stopped pending Exec producer alive. A real systemd
StopUnit request with an invalid unit name is rejected and its callback returns
False; the adapter reports Busy without claiming quiescence. This is a real
rejected request, not a disconnect after systemd accepted a valid target stop.

## Observed callback gap and bounded refusal

Inside a revocation callback the controller releases the pending Exec producer;
it acquires its name. The historical fixture's stop callback only knows target
Exec descriptors recorded by completed Probe observations in LIVE.json. The
Exec producer is absent there, so the callback stops the registered target
SystemdService and misses Exec. Actual UID1002/owner/pidfd observation detects
remaining activity and the unchanged adapter raises UnverifiedQuiescence with
a zero settle window. No success or account publication is allowed. This
reproduces a gap in the old fixture's observation callback, not a production
controller already installed on the host.

The root fixture explicitly revalidates the pinned Exec descriptor and registers
that observation. Fresh authorized stop then binds PID/executable/cgroup and
stops the original producer through systemd. Both pidfds signal exit, all target
names/processes are absent and new activations of all four routes fail. Owner
journals and admission bytes remain unchanged, including idempotent retries.
The final whole-account coordinator `_check` refuses missing families without
legacy resume. PAM target remains denied224 with a causal fixture journal;
peer manager/proof, payload PIDs and broker PID444 remain intact.

Both original pending clients finally report activation cancelled because the
bus name was released. The evidence does not claim their original requests
succeeded. Late payload name acquisition is proven separately by the owner
check/actual Probe. SIGSTOP/SIGCONT schedules the two root-selected interleavings
explicitly; it is not an exhaustive scheduler/race exploration. The new pending
observer is a trusted VM fixture, not production discovery or a coverage issuer.

## Evidence and restoration

```sh
python3 docs/evidence/parental-pending-activation/verify-evidence.py
```

Source/artifact hashes bind the new delayed C payload, observation helper,
unchanged historical dependencies, native logs, expected refusal paths and
restoration readers. Independent inspections confirm original PAM bytes/mode,
vendor PAM, passwd/group, absent reserved routes/retirements/units/executable/
policy/ledger/catalog/module/proofs/registry/roles/linger, zero relevant
processes/managers/runtime/sessions, Permissive and disabled/inactive SSH.
No packages installed or shared bus restart/stop. QEMUexit0; VM powered off.
Root helpers/backups/logs remain; cleanup is scoped, not whole filesystem
rollback or complete kernel audit.

Production pending discovery, exhaustive namespace coverage, valid-stop
response-loss, concurrent catalog changes, broad activation/reload/stop races,
coordinator/GUI disconnect, power loss, global monotonic authority/antirollback,
NSS lifecycle, complete GDM, Polkit, privacy/UI and ISO remain unqualified.
Next: replace completed-only observations with verified pending-producer
inventory and bounded recapture in an isolated controller, before full coverage
and product integration. Scope discussion is recorded separately in
`docs/parental-first-release-scope.md`; it does not change the authorized contract.
