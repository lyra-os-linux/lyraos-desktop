# Boot integration on Leap 16.1

The September 15 reference-machine check identified missing Wi-Fi regulatory
data, a malformed Plymouth runtime path, and the GNOME recorder compatibility
launcher being bypassed by GDM. These corrections are included in the next
Desktop recipe; the ISO itself still needs a local build and boot qualification.

## Wi-Fi

`wireless-regdb` is an explicit image dependency. Hardware firmware packages do
not guarantee that `regulatory.db` and its detached signature are installed when
the image uses `onlyRequired`. Use the signed RPM from the matching official
Leap release. Do not override country restrictions or replace the database with
unsigned data. On the reference machine, installing the package and running
`iw reg reload` succeeded while the connection remained active.

## Plymouth

Leap 16.1's `plymouth-22.02.122+94.4bd41a3-160100.2.1` leaves
`${localstatedir}` in the daemon's PID argument and in the password-agent unit's
`ConditionPathExists`. The startup drop-in selects `/run/plymouth/pid` explicitly.
The password-agent override is otherwise semantically identical to the vendor
unit. A complete override is necessary there because systemd still parses and
warns about the malformed vendor condition before processing a drop-in.

The dracut configuration carries these files into installed-system initrds.
It does not add Plymouth or DRM modules to the generic live initrd. Keep the
existing live-ISO Plymouth exclusion. Remove these overrides after the vendor
units resolve the path correctly and a new boot is qualified. Recheck the full
password-agent unit against upstream whenever Plymouth changes.

The legacy `KillMode=none` deprecation remains in the vendor startup unit.
Changing process termination during the splash/GDM handoff solely to silence
the warning is outside this path correction and needs its own lifecycle test.

## GNOME login

The installer used to delete `/etc/gdm/custom.conf` as a live-only artifact.
With neither that file nor a sysconfig/runtime backend present, GDM 48.0 reports
`settings->backends != NULL` on settings reads. The file belongs to
`gdm-branding-openSUSE`, so verifying only the `gdm` RPM misses this deletion.
This is an installer cleanup bug, independent of the GPU or NVIDIA driver.

The installer now preserves unrelated GDM settings and explicitly disables
automatic and timed login. It removes their account/delay keys, handles repeated
daemon groups, and recreates the backend if missing when GDM is installed.
Other display managers retain their existing cleanup. `lyra-system-smoke`
checks the installed configuration instead of treating its existence as a live
artifact. The live image still enables `liveuser` autologin in `config.sh`.

The installed GDM 48.0 reader was exercised in disposable namespaces with a
private D-Bus, isolated syslog and no host session access. The missing-file
baseline reproduced the assertion; the repaired configuration eliminated it.
This tests configuration loading, not the complete graphical login or an ISO.

On the reference machine the missing file was restored with only the two
autologin enable flags set to `false`, owned by root with mode 0644. The receipt
is `/var/lib/lyra-os-theme/gdm-settings-repair-20260915/manifest.json`.
GDM PID 1347 and personal Shell PID 2122 remained active; neither service was
restarted. Rollback is removal of the newly created file only if its SHA256
still matches that receipt; there was no previous file to restore.

The next actual boot on September 15 at 16:18:22 validated the backend repair:
no settings assertion, unchanged configuration checksum, password login and
an active Wayland session with zero Shell restarts. Both managers had zero
failed units. This validates the reference machine, not a published installer
RPM, a newly built ISO or other hardware. The greeter Xwayland exception still
occurred at 16:18:37 in PID1414; personal Shell PID2104 remained active.

The separate greeter bus is deliberate in
[GDM 48.0's session launcher](https://github.com/GNOME/gdm/blob/48.0/daemon/gdm-session.c):
it wraps greeter sessions in `dbus-run-session` to avoid systemd session-lookup
conflicts across seats. Therefore the `org.freedesktop.systemd1` activation
messages on that bus do not by themselves demonstrate a failed user manager.
Do not force the greeter onto the user manager or disable Xwayland to silence
these messages. Their upstream handling remains separate from the backend fix.

See [the recorder compatibility documentation](gnome-screencast.md). The GDM
override uses its own first-priority service directory; normal-user sessions
keep the `/usr/local/share` override. A private session bus using GDM's data
search order successfully activates the recorder and reports
`ScreencastSupported=true` without capturing the user's screen.

The next reference-machine boot at 15:58 on September 15 confirmed successful
GDM recorder activation and no recurrence of the corrected module, regulatory,
legacy-extension or Plymouth-path errors. Both system and user managers reported
zero failed units. The separate Xwayland exception recurred when the greeter
ended after login; the personal Shell remained active with zero restarts.
ACPI firmware-table errors are also outside this change. The
[ISO fix tracker](iso-fix-tracker.md) records the remaining work and hardware scope.

## Reference-machine cleanup only

The unsigned orphan `linuwu_sense` module and its forced-load configuration,
plus the blacklist of the signed `acer_wmi` replacement, were backed up and
retired. The in-tree SUSE-signed Acer driver loaded successfully. No Secure Boot
setting was changed. Extra Linuwu/DAMX controls are not claimed as supported by
the in-tree driver; no Linuwu module had been working in the diagnosed boot.

Five old Sheliak preview files were also backed up and removed from the obsolete
UUID directory. They were not RPM payloads and are not installed by the current
ISO recipe. Do not turn this machine-specific cleanup into a wildcard removal
script in the package.
