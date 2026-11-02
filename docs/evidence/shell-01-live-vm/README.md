# SHELL-01: patched gnome-shell in the RC 3 live session

Collected on 2026-11-02 in a disposable QEMU/KVM guest booted from the exact
`LyraOS-Desktop-16.1-rc.3-x86_64.iso`, SHA-256
`50211bcf31271d232ea4326fc46704cad79a729d1bb363679ce32829d7794a3a` (the frozen
RC 3 promoted to 16.1). UEFI (OVMF), no disk attached, Intel HDA codec and an
xhci bus for `usb-audio` hotplug. Tools: `packaging/gnome-shell/tests/vm/`
(`run-live-vm.sh`, `qmp.py`, `shell01-guest.sh`). The guest script runs as a
transient system unit so it survives the GDM restart, and writes one JSON line
per observation to the virtio port `org.lyraos.UpgradeEvidence`. The live
journal was forwarded to the host serial log; the relevant lines are in
[serial-journal-excerpt.log](serial-journal-excerpt.log).

| Phase | Result |
| --- | --- |
| [baseline](baseline.jsonl) | SUSE `gnome-shell` 48.8-160100.2.1, libgvc `7f5dd924…`. Audio plays. The deterministic zero-profile card test **crashes** (exit 139, SIGSEGV), the same failure as the station. |
| [plan](plan.jsonl) | `zypper install --dry-run --name --from lyra-shell-staging --no-recommends` with the exact editions: **3 packages to upgrade, 3 to change vendor** (`gnome-shell`, `gnome-shell-lang`, `gnome-extensions`; SUSE → `obs://build.opensuse.org/home:rodrigosbrito`). No other package, removal or new dependency. |
| [install](install.jsonl) | All five staging RPMs match `SHA256SUMS`; the three installed subpackages pass `rpm -K` and `rpm -Uvh`; `rpm -V gnome-shell` is clean. GDM restarted and auto-logged in. |
| [verify](verify.jsonl) | New shell PID 4231 is the Wayland compositor and maps libgvc `930afb88…` (the staging build). Audio plays, volume can be set, the deterministic test prints **SURVIVED**. |
| [hotplug](hotplug.jsonl) | 10 `usb-audio` add/remove cycles: every card appears and disappears, shell PID stays 4231, no new coredump or shell error. |
| [select-lineout](select-lineout.jsonl), [select-spdif](select-spdif.jsonl) | Choosing *Line Out* and then the USB *Digital Output (S/PDIF)* in Quick Settings changes the default sink; S/PDIF needs a card profile change through libgvc. |
| [final](final.jsonl) | Removing the selected USB output falls back to the built-in sink. Same shell PID; the only coredump of the boot is the intentional baseline `gjs` crash. |

Screenshots: [volume OSD](ui-osd.png), [Quick Settings with USB audio](ui-qs-usb.png),
[Sound Output menu](ui-out-menu.png).

## Limits

The race itself (PipeWire announcing a card before its profiles) was not
reproduced in the VM; the deterministic test injects exactly that state. The
live session installs RPMs directly into its overlay. It does not qualify the
Updater `PackageMigration` lifecycle, Snapper rollback, an installed system,
physical hardware or a candidate ISO containing the package.

In the first boot of this VM the live session ended by itself after about 45
idle minutes and GDM showed a password prompt that `liveuser` cannot satisfy.
The journal of that boot was lost (volatile live journal); see the observation
recorded in `docs/iso-fix-tracker.md` under SHELL-01.
