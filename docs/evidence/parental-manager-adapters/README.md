# Experimental classification and user-manager adapters

This gate adds two real, narrowly scoped adapters to the ordinary admission
withdrawal prototype. It does not install a parental-control service or qualify
all account execution routes. Root and administrator actions remain trusted.

Classification verifies the complete root-selected account tuple through NSS,
the withdrawn operation and proof hash in the protected marker and retired
journal, absence of the positive ordinary proof, and the installed fixture PAM
bytes/module with SELinux Enforcing. A shared per-UID snapshot lock is held
through scoped effects and the classification is revalidated afterward. The
fixture verifies file ownership, type, permissions, links and contents; this is
not an upstream PAM integration audit or a production integrity mechanism.

User-manager revocation requires a separate explicit authorization callback.
It uses logind terminate-user and systemd stop of only the verified UID's manager
and runtime units. It never kills arbitrary processes, changes NSS or removes
the admission barrier. Completion requires observed absence of the manager,
runtime, UID processes and logind user object. A bounded 25-second wait accounts
for asynchronous logind teardown; expiry refuses completion. Authorization is
trusted test injection, not Polkit or an authenticated transport.

The initial native attempt refused UnverifiedQuiescence immediately after the
stop commands because logind teardown was asynchronous. Its failed result,
logs, original adapter and successful cleanup are retained in failed-attempt-1;
it is not counted as a passing gate. The final complete run uses the bounded
wait and is the only passing matrix counted here.

The final VM matrix checks both existing ordinary-user managers, withdrawal
without implied process quiescence, denied/wrong-operation/changed-PAM requests
without manager termination, real authorized revocation with peer preservation,
PAM rejection of fresh target admission, idempotent revocation with unchanged
negative authority, refusal of the full coordinator with only these two
adapters, a root-enabled linger marker with no observed target reactivation,
manual PAM refusal while linger exists, and fresh admission of the other user.
The linger observation is bounded; it is not a reboot or indefinite stress test.

The coordinator still requires classification, GDM, user-manager, SSH, system
units, D-Bus activation and cron. It rejects UnsupportedProducer before calling
adapters when any route is missing. Native revocation is therefore tested via
the scoped adapter directly, not represented as successful full coordinator
execution. The classification adapter's quiescent/revoke methods only validate
its snapshot; process quiescence belongs to the user-manager adapter.

No host, recipe, RPM, OBS or ISO parental changes. No account creation, NSS
mutation, enrollment, ordinary-role reactivation, monotonic/global revision,
boot recovery, power loss or lifecycle UID-reuse qualification in this gate.
Issues #6/#102 remain open and parental controls remain NO-GO.

Restoration preserves PAM bytes/mode, vendor configuration and account files;
removes fixture state, module and linger; stops managers/runtime/processes;
returns to Permissive; independent restore-check confirms the VM baseline.
Ordinary manager-created files in user homes are not a complete filesystem
rollback. The VM is then powered off. Historical protocol sources are reused
without modification and their hashes are recorded.

Run `python3 docs/evidence/parental-manager-adapters/verify-evidence.py` for the
offline evidence check, and `python3 -m unittest discover -s tests` for unit and
repository regressions. Native helpers assert both dedicated kernel markers,
root execution and the disposable disk serial before any fixture mutation.
