# GDM greeter Xwayland exception — reproduction, September 15, 2026

The greeter reports `Xwayland exited unexpectedly` when GDM ends its session
after a successful password login. The new user's GNOME Shell remains active.
The same exception reproduces with official openSUSE Leap RPMs without NVIDIA
or Lyra extensions. Evidence points to the order of greeter termination in
GDM/Mutter, rather than a dependency on Lyra's extensions or the NVIDIA driver.
BOOT-06 remains open for upstream investigation; no lifecycle workaround was
applied to the product.

## Environment and scope

Two disposable QEMU/KVM component VMs used the same official Leap 16.1 RPM
base, kernel `6.12.0-160100.4-default`, two vCPUs, 3 GiB RAM and virtio graphics
with Mesa software rendering. They used GDM 48.0, GNOME Shell/Mutter 48.8 and
Mesa-dri 26.0.7, matching the reference machine's relevant package versions.
The [evidence manifest](evidence/gdm-greeter-20260915.json) records exact RPM
releases, process IDs, results and hashes of the retained local logs.

The baseline retained the vendor `gdm-branding-openSUSE` configuration. The
Lyra scenario added the six extensions from the signed published Sheliak
2.0.2 RPM, GNOME defaults and GDM recorder integration from Desktop commit
`9584dc974039424cf15917feb939ef9f1178b515`. It used the installed-system GDM
configuration with automatic and timed login disabled. All six Lyra components
reported active in the user's session.

These are minimal GNOME/GDM environments, not complete installed Leap or Lyra
ISOs. Optional desktop services and the complete application/branding set were
not installed. In particular, the recorder comparison includes the greeter
override, not qualification of recording in the user's session. Neither VM
contains an NVIDIA GPU or driver. The result does not qualify physical GPU
acceleration, Secure Boot, firmware, suspend or a release ISO checksum.

## Results

| Check | Official Leap RPM base | Same base with Lyra components |
| --- | --- | --- |
| Password login, lock, unlock, logout | 3 complete cycles passed | 3 complete cycles passed |
| User Shell PID across each lock/unlock | Preserved | Preserved |
| User Shell / GDM restarts | 0 / 0 | 0 / 0 |
| Failed system units at cycle completion | 0 | 0 |
| Greeter Xwayland exception in those logins | 3 of 3 | 1 of 3 |
| Exception emitted by user UID 1000 | No | No |

The sample is small and the failure is timing-sensitive. The different counts
do not establish an improvement or regression from Lyra. Both environments
reproduce the same greeter exception while completing normal session actions.

One additional traced login in each VM investigated termination. These extra
logins are separate from the six functional cycles above:

- In the baseline, GDM PID 378 called `kill(-2556, SIGTERM)`. Greeter Shell
  PID 2571 and Xwayland PID 2592 belonged to that process group. Xwayland received
  SIGTERM from PID 378 and exited with status 0. Tracing GDM, Shell and Xwayland
  together changed the timing: the exception did not recur in that login.
- In the Lyra scenario, tracing GDM alone recorded
  `kill(-2726, SIGTERM) = 0` at Unix time `1789502713.933623`. The greeter Shell
  PID 2741 belonged to that group and logged the Xwayland exception at
  `1789502713.937436`, **3.813 ms later**. The user Shell remained active with
  zero restarts. A second kill of the already-ended group returned ESRCH,
  matching the separate GDM message about an already-dead child.

The observed signal source and timing support a shutdown-order race. They do
not prove that every Xwayland error on every GPU has the same cause. The
reference machine has the same exception during the same login transition;
that correspondence supports investigating this common path before changing
its working driver stack.

## Relevant upstream paths

[GDM's launch environment](https://github.com/GNOME/gdm/blob/48.0/daemon/gdm-launch-environment.c)
sends SIGTERM to the greeter process group in `gdm_launch_environment_stop()`
and again when its conversation stops. The negative process ID selects the
group. [Its signal helper](https://github.com/GNOME/gdm/blob/48.0/common/gdm-common.c)
passes that ID to `kill()`.

[Mutter's Xwayland handling](https://github.com/GNOME/mutter/blob/48.8/src/wayland/meta-xwayland.c)
treats a lost X connection as an error when X11 is mandatory. That path emits
the exception observed here. Its normal shutdown path replaces the X I/O error
handlers, which is relevant when investigating termination order. The trace
establishes the externally observed signal sequence; it does not establish a
safe code change to these internal paths.

## Reproduction for upstream

1. Use a regular password-authenticated GNOME Wayland session with the package
   versions in the manifest. Keep GDM's vendor configuration present and
   automatic login disabled. A virtual GPU is sufficient for this reproduction.
2. Wait for the greeter, log in, lock and unlock the screen, then log out.
   Repeat three times. Do not restart or kill the user's Shell as part of the
   test.
3. Collect the boot journal, greeter/user UIDs and their GNOME Shell PIDs.
   Correlate the exception with GDM ending the greeter after the new session
   registers. Confirm the user Shell remains active and its restart count stays
   zero. Check GDM and failed system units separately.
4. If tracing is needed, first reproduce without a tracer. Then trace only the
   GDM daemon's signals around login; tracing the Shell or Xwayland can perturb
   the timing. Record process groups before login and preserve microsecond
   timestamps in both the trace and journal.

Useful read-only evidence commands, with sufficient permission to read the
system journal:

```sh
journalctl -b -o short-precise _COMM=gnome-shell
journalctl -b -u gdm.service
loginctl list-sessions
systemctl show gdm.service -p MainPID -p NRestarts
systemctl --user show org.gnome.Shell@wayland.service -p MainPID -p NRestarts
```

This report is prepared for upstream review; it has not been filed as a new
upstream issue. Keep the remaining ISO/hardware checks in
[the fix tracker](iso-fix-tracker.md). Do not treat disabling Xwayland, changing
PAM/bus architecture or filtering the message as a demonstrated correction.

## Evidence retention and publication

Raw journals, screenshots, process snapshots and signal traces are retained in
`analysis/2026-09-15/gdm-vm-comparison/` in the Lyra workspace. Test VMs, disks,
initramfs and installed guest roots were removed after collection; their cleanup
receipt is retained there. No physical-machine package, graphical session or
GDM configuration was changed by the comparison.

The separate GDM settings/backend repair BOOT-09a was integrated by
[Desktop PR #85](https://github.com/lyra-os-linux/lyraos-desktop/pull/85).
Its installer RPM `0.1.0-lp161.33.1` is published in the release repository via
[OBS request #1378217](https://build.opensuse.org/request/show/1378217).
The RPM signature and embedded source commit `9584dc9` were verified after
publication. This repair preserves the GDM configuration; it does not fix the
independent greeter exception described here. KIWI recipe changes are in Git
and still require a newly built candidate and its hardware qualification.
