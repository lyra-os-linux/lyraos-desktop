# Signed portal migration with the published Updater RPM

Collected on 2026-09-28 in a disposable Btrfs guest. The original parental
fixture, host packages, release repository and candidate ISO were not changed.

Recheck the collected file hashes and result consistency with
`python3 docs/evidence/portal-updater-native/qualify.py`. This checks retained
evidence; it does not rerun the VM lifecycle.

[Updater 0.2.9](updater-rpm.json) was built from commit
`3cc51f7d051ab77a8f751ec8d4e705a7b633e751`, published only for Leap 16.1 in
OBS staging revision 42, and verified against the repository signature and
build API. RPM SHA256:
`92c149a89959cb52ddd214ab4a99b761c6a8bc8a76d85e6873ff8dfde3ddf2b0`.
The installed service, offline worker, verifier and public key match that RPM.
There are no local executable or offline service overrides.

## Principal package without translations

[Result](main/verified.json): native UEFI, GRUB and installed kernel/initrd;
unprivileged preview; native Polkit authentication; root replan, download,
signature verification and Snapper snapshot; real offline service; automatic
reboot; native post-boot verifier `Completed/Passed`.

The VM used `-no-reboot`, so the hypervisor exited when the guest requested a
reboot. The complete [offline serial log](main/offline-serial.log) records that
phase; no manual reboot request was sent during it. A new native boot ran the
verifier. [Installed inventory checks](main/main-success.json) confirm that
only the exact portal RPM changed. Translations remained absent, repository
and boot files were unchanged, and sequence 1 was consumed only after success.

Authentication used the shipped Polkit action and a separate unprivileged
`pkttyagent`. The fixture account's original password hash was restored before
Start created its snapshot and checked against that snapshot. No password or
shadow hash is retained in this evidence.

## Principal package with installed translations

[Result](lang/verified.json): the same complete native lifecycle passed from a
fresh baseline with the original SUSE language package installed. The plan and
[resulting inventory](lang/lang-success.json) contain exactly the portal and
its language package, both moving to the signed Lyra build. No other package,
repository or boot file changed. Reboot was automatic and the verifier completed
with `Passed` before sequence 1 was consumed.

## PackageKit coexistence

[Three native boots](packagekit/verified.json) used the offline worker extracted
from the same published RPM. Foreign and absent markers and the occupied-lock
case passed without taking over another updater's transaction.

## Failure and authenticated rollback

[Result](rollback/verified.json): a fixture service returning failure was
created after the migration snapshot, without editing the operation state.
After the real offline update and automatic reboot, the native verifier
reported `NeedsRecovery/POST_BOOT_FAILED_UNITS` and did not consume sequence 1.

The shipped service accepted `AcknowledgeRecovery/Rollback` through native
Polkit authentication. Snapper selected its writable snapshot; its parent UUID
and default subvolume matched the recorded recovery intent. The next ordinary
UEFI/GRUB boot required no manual snapshot selection and ended with
`Completed/Passed`, `rollback-verified`.

The complete original RPM inventory, including both SUSE portal packages, was
restored. Repository and boot hashes matched the baseline, the injected fault
unit disappeared with the snapshot restoration, no failed units remained,
and the manifest sequence remained unconsumed. Updater binaries still matched
the published 0.2.9 RPM.

## Remaining gates and limits

These tests use the existing [official testing manifest](../portal-migration-manifest/README.md)
at immutable commit `085f91bce424172df1ab717ce0664a6bb919f0bc`, unchanged signed
bytes and shipped public key. Its minimum Updater is still 0.2.7. The final
delivery must require at least 0.2.9 and obtain a new signature: the 0.2.7
unprivileged Snapper check and 0.2.8 automatic reboot path failed in the native
rehearsal and were corrected by Updater PRs 28 and 29.

The guest runs SELinux permissively and uses TTY authorization. This does not
qualify the GNOME graphical dialog, enforcing parental policy, production
promotion or the final ISO. Portal migration is a dependency of parental
protection, not completion of that product feature.
