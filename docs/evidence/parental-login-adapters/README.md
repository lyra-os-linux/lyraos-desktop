# Experimental GDM password and SSH login adapters

This gate extends ordinary admission withdrawal with scoped real login adapters.
It is an isolated prototype, not parental-control deployment or a production
GDM/OpenSSH integration qualification. Root and administrators remain trusted.

`LoginRoute` composes the earlier classification and native user-manager
revocation adapters. It checks a root-selected route's installed admission
configuration before authorization, after authorization under the shared UID
snapshot lock, and after revocation. Revocation is explicitly authorized and
uses logind terminate-user and systemd stop of the verified UID's manager and
runtime. It does not stop the shared SSH listener or GDM daemon. Completion has
a bounded wait and requires the scoped process observer to return literal True.
It is account-wide revocation: all sessions of that UID can be terminated.
Authorization callbacks are trusted fixtures, not Polkit or a secure API.

SSH needs an account-stage gate before forwarding and subsystem access.
`ssh-ordinary-guard.c` includes the unchanged earlier withdrawal session guard
and adds ordinary-only PAM account management. It requires the protected UID
snapshot lock, absence of either negative marker/journal, a positive ordinary
proof matching name/UID/GID/group, and SELinux Enforcing. Account management
precedes pam_selinux open; it does not assert a pending MAC label. The included
session hook checks the pending ordinary MAC label at session opening. Unknown
and supervised accounts are denied by this experimental SSH account route.
There is no cached positive permission or writer operation in either reader.

The native matrix opens GDM password authentication with a bounded ELF session,
SSH commands, no-shell forwarding and multiplexing for existing ordinary UID
1002, while preserving UID1000's commands and tunnel. It records root SSH
monitors inside the target's user slice and the exact GDM PAM worker associated
with that user's session-open event. Kernel pidfds observe those processes'
exit in addition to absence of UID processes, user-slice processes, manager,
runtime and logind user object. pidfd counts include separately pinned records
and are not presented as a count of unique processes. No custom root signals.

Withdrawal alone leaves old GDM/SSH sessions and a multiplexed channel alive.
Denied revocation and a changed SSH PAM stack leave them running. Authorized
native revocation closes the target sessions and monitors while preserving
both daemons and the peer. GDM's repeat revocation preserves negative authority.
New SSH command, SFTP, forwarding, old-mux fallback authentication and GDM
password admission are rejected with exact fixture PAM causes. The other user
can open fresh SSH and GDM sessions and retains its old tunnel and command.
A changed GDM configuration refuses an inhibition claim. The full coordinator
with only classification, user-manager, GDM and SSH still rejects missing
system-units, D-Bus activation and cron before invoking route callbacks.

GDM uses the prior explicitly hashed diagnostic worker and fixture launcher
policy, restored after the test. This tests the password PAM/greeter protocol,
not the official worker, full GNOME/compositor, visual login UX, autologin,
timed login or every GDM route. The fixture disables automatic and timed login;
the adapter does not discover all producer configurations. SSH is one loopback
listener with root-selected settings and keys, with IP penalties disabled to
avoid confusing rate limiting with a PAM refusal. No remote exposure,
rate-limit qualification, pending authentication conversation or stress test
is claimed. All-producer and production qualification flags remain false.

The first four native attempts failed and are retained separately. Attempt 1
refused the SSH baseline because the read-only fixture policy omitted OpenSSH's
separated session/authentication domains; its journal records sshd_session_t.
Attempt 2 selected GDM's internal already-running-session socket. Attempt 3
completed target revocation but attempted a removed greeter socket during
readmission. The driver now identifies the first new live greeter endpoint in
the current GDM invocation and waits for its display registration. Attempt 4 waited for automatic greeter recovery, which this bounded ELF
fixture does not qualify. The final matrix explicitly recreates the GDM
display after recording daemon preservation during revocation. This reset is
a controller fixture operation, not an adapter effect; peer SSH remains live.
Only the complete final matrix of 25 passing controls counts as this gate's
native result. The earlier
GDM configuration serialization was also corrected to preserve key case.

Each attempted matrix restores declared fixture paths and removes login
modules/policies/keys/units/payload. The final restoration additionally tracks
shadow's backup; earlier attempts did not track that backup and are not a whole
filesystem rollback. Passwords and private keys are never exported. A read-only restoration checker initially had an undefined config reference;
its failure and original source are retained, and the corrected checker was
rerun successfully. The GDM technical user is independently checked for no
processes or logind state. PAM bytes,
modes, owners and labels; GDM worker/helper/desktops/AccountsService; shadow and
its tracked backup; vendor files and account tuples are checked. Managers,
runtime, sessions and fixture processes are stopped, SELinux is returned to
Permissive and the VM is powered off after an independent restore check.
Root evidence helpers/backups and normal user-home side effects remain; this
is not an immutable disk snapshot restoration or a complete kernel audit.

No host, recipe, RPM, OBS or ISO changes. No account creation, account/group ID
mutation, enrollment, ordinary-role reactivation, global monotonic journal,
boot/power-loss/recovery qualification. Issues #6/#102 remain open; parental
controls remain NO-GO. All historical sources retain their original hashes.

Run `python3 docs/evidence/parental-login-adapters/verify-evidence.py` to inspect
archived results and source hashes. Repository regression suite (344 passing tests, including 10 new route
decision tests):
`python3 -m unittest discover -s tests`.

The raw stderr of failed attempt 4 retains its original final blank line.
Source whitespace checks exclude only that captured log; it remains hash-checked
byte for byte as evidence rather than normalized to pass a source formatter.
