# Development pause checkpoint — 2026-09-01

## Completed

- Restored the flavor-neutral installer highlight to `Security`, `Segurança`
  and `Seguridad`, with the shield icon and localized supporting copy.
- Added a regression test that rejects the old `Integrated GNOME` highlight.
- Passed all 180 Python repository tests and the OBS package's 100 Rust tests
  (one environment-only test ignored as expected).
- Pushed source commits `87e0b1c` (Lyra OS 1.1 Alpha 7 and installer fix) and
  `7ae0a96` (retire Leap 16.0 from the OBS release contract).
- Published staging `lyra-installer-0.1.0-lp161.30.1.x86_64` and verified its
  OBS signature and SHA-256.
- Accepted OBS request `1375222` and published release
  `lyra-installer-0.1.0-lp161.27.1.x86_64`; the Lyra, Vega and Fina release
  channel gate passed with all configured targets published.
- Verified the public release RPM signature. Its SHA-256 is
  `e991ebd8639468d1b10d6d9d9c6778f3b6f434695684fedc2e6bf53498c2daaa`.

## Paused at

The clean GNOME ISO rebuild used `--published-installer` and successfully
installed/configured the complete rootfs, including the promoted installer.
KIWI then failed while copying the generated SquashFS:

```text
OSError: [Errno 5] Input/output error:
'/var/tmp/kiwi_9wdxg1fn' ->
'/tmp/lyraos-desktop-gnome-1.1-security-test-1001/build/live-media.keyixjsk/LiveOS/squashfs.img'
```

No corrected ISO was produced and no VM was opened. The earlier GNOME, KDE and
XFCE ISOs predate release installer 27.1 and must not be treated as the final
test candidates.

## Resume from here

1. Diagnose the one-off `EIO` without deleting the failed workspace; check the
   kernel/filesystem log and verify large-file copies between `/var/tmp` and
   the selected build filesystem.
2. Rebuild GNOME in a fresh persistent workspace with `pkexec` and
   `--published-installer`, then confirm the image manifest contains
   `lyra-installer-0.1.0-lp161.27.1` and `linuxtoys-6.7.1-lp161.1.1`.
3. Run the full ISO audit, then boot with Secure Boot and complete an install
   plus first boot test.
4. Rebuild/audit KDE and XFCE against the same installer release before their
   VM tests.

Failed workspace and log:

```text
/tmp/lyraos-desktop-gnome-1.1-security-test-1001
/tmp/lyraos-desktop-gnome-1.1-security-test-1001/lyra-os-test.log
```
