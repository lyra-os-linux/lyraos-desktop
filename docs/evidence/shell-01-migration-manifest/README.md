# SHELL-01 testing manifest (sequence 3)

Prepared on 2026-11-02 for the [gnome-shell libgvc fix](../../../packaging/gnome-shell/README.md).
`releases-v1.json` was produced by `lyraos-desktop-updater/scripts/release-manifest.py`
and handed off by `scripts/signing-handoff.py`; both validate and canonicalize the
document. Canonical SHA-256:
`6be7f5b5034201a146fda7c3581feb24258a755dd67751247207bdfeb22b8273`.

Compared with the [portal sequence-2 manifest](../portal-migration-manifest-029/README.md):

- source and target: the installed 16.1 identity (`16.1`, `lyra-release-16.1`,
  desktop, x86_64) instead of 1.1;
- `package_migration`: `gnome-shell` (mandatory) and, only when installed,
  `gnome-shell-lang`, `gnome-extensions`, `gnome-shell-calendar` and
  `gnome-shell-devel`, all `48.8-160100.2.1` (SUSE) →
  `48.8-160100.2.1.lyra1.160100.1` (OBS), with the staging RPM hashes;
- the vendor grant lists exactly those five names;
- repository alias `lyra-shell-staging` (staging, priority 99) instead of
  `lyra-portal-staging`; every other repository is unchanged;
- `sequence` 3, `status` `testing`, valid 2026-11-02 → 2026-11-16 UTC.

`minimum_updater_version` stays 0.2.9, the version in RC 3.

## Policy audit

[audit.rs](audit.rs) parses these bytes with `lyra-upgrade-core` from the
published 0.2.9 source commit `3cc51f7d051ab77a8f751ec8d4e705a7b633e751`
([result](policy-audit.json)). With the RC 3 inventory it plans exactly
`gnome-shell`, `gnome-shell-lang` and `gnome-extensions`, matching the
[real zypper dry run](../shell-01-live-vm/plan.jsonl). It refuses the stable
channel, Updater 0.2.5–0.2.8, the consumed sequence, omitting an installed
subpackage, adding an absent optional one, an unrelated same-vendor change and
an unknown source edition (for example a future SUSE `160100.2.2`); an already
migrated system has nothing pending. To rerun: build it as a binary crate
depending on that commit's `core/` and run it next to `releases-v1.json`.

## Signing

Review these bytes and create the detached signature with the unchanged
official key, in the authorized environment:

```sh
sha256sum --check SHA256SUMS
gpg --armor --detach-sign \
  --local-user 01B63EEDBE6B079126A0116EFA7353A131ECEFEB \
  --output releases-v1.json.asc -- releases-v1.json
```

Signed by the maintainer on 2026-11-02 19:43 UTC. The private key was
decrypted only in a temporary `/dev/shm` GNUPGHOME and removed afterwards.
[signature-verified.json](signature-verified.json) records the `VALIDSIG`
against the unchanged public key shipped by the `lyra-upgrade` 0.2.9 RPM.
Signature SHA-256: `d152c65a2b1a6f7fec7acf81508e95ba041964f9e08c3a589e66ba74166fea2d`.

## Remaining gates

1. The native lifecycle on an installed RC 3 Btrfs VM with
   `/etc/lyra-upgrade/channel` = `testing` and the immutable commit URL as
   `testing-manifest-base-url`: preview, authenticated Start, snapshot, offline
   application, reboot and `Completed/Passed`, plus an explicit rollback run.
   The live session cannot qualify this; it has no Snapper or installed boot.
2. Promotion of `gnome-shell` to `home:rodrigosbrito:lyra` and a separate
   `stable` manifest with `repo-lyra` as the source repository and the release
   RPM hashes. The 0.2.9 stable endpoint is
   `https://downloads.sourceforge.net/project/lyra/releases/1.1/desktop/releases-v1.json`
   (404 on 2026-11-02: no production manifest has ever been published there).
   That manifest reaches every installed system: it needs its own sequence
   allocation and maintainer review before publication.
