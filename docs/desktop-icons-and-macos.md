# GNOME desktop icons, MacOS X and the next image

The maintainer requested files and icons on the GNOME desktop, a MacOS X profile,
and an independent Vega GTK switch to disable desktop icons without deleting
files. GNOME remains the only desktop release target. These changes belong in
the next ISO together with the fixes delivered through 11 September 2026.

The ISO is built locally with KIWI from this repository. OBS supplies RPMs only;
this change updates the local image recipe and does not submit an ISO build.

Use upstream [Desktop Icons NG](https://gitlab.com/rastersoft/desktop-icons-ng)
in an RPM, retaining the base package name `gnome-shell-extension-desktop-icons`.
A separate Lyra implementation would duplicate maintained file operations and
Nautilus integration. The GTK4 fork adds features beyond the requested file/icon
scope. The base Leap package inspected during development supports GNOME 45–47;
its metadata must not be bypassed on GNOME 48. The selected stable upstream tag
49.0.5, commit `c32667693d0831c29e3ab3f7bfeb675ea1531a00`, supports 46–49.

The spec in `packaging/desktop-icons` declares the GTK3/GJS, GnomeDesktop,
GnomeAutoar, Adwaita and Nautilus runtime dependencies. Produce its source archive
from that exact commit with `git archive --format=tar.gz
--prefix=desktop-icons-ng-49.0.5/ c32667693d0831c29e3ab3f7bfeb675ea1531a00`, writing
`desktop-icons-ng-49.0.5.tar.gz`. The RPM builds translations and schemas and
checks the metadata. It does not install arbitrary extension downloads at login.

The GNOME image explicitly selects this package and enables `ding@rastersoft.com`
through an unlocked GSettings default for new/live users. Existing users retain
their extension preferences. Vega GTK's Active desktop switch is independent of
all six profiles. Disabling it removes icons from the desktop; files remain in
the user's Desktop folder and accessible through Nautilus. A globally disabled
Shell extension setting is respected, and failed writes restore the switch.

MacOS X requires Vega GTK >=5.1.34, Sheliak >=1.16.0 and Welcome >=0.4.0. It uses
a centered floating bottom dock, icon magnification and a flush top bar with the
L application menu at the left. Existing profile settings migrate without losing
favorites, Windows menu cards or saved dock preferences.

## Image qualification

`kiwi/config.sh` runs `check-gnome-image.py` inside the prepared image. It rejects
stale versions of these components, the DING/Shell mismatch found in Leap, and
older theme, icons, Nautilus/LibreOffice branding, LinuxToys and common GNOME
packages. The separate OBS provenance/signature gates still require accepted
source revisions; minimum versions cannot distinguish different sources that
reuse the same version. Do not replace the immutable historical OBS baseline.

Before releasing the next ISO:

- Publish and qualify the new RPMs through the existing staging/release process.
- Record the actual signed package inventory and accepted source revisions.
- Verify live login and first installed login, all six profiles, light/dark
  colors, menu/favorite preservation and the Active desktop switch in PT/EN/ES.
- Verify files, folders, Trash, mounted volumes and drag-and-drop with Nautilus;
  include multi-monitor/HiDPI, suspend/resume and a fresh user.
- Retain installer, firmware, hardware, update and rollback release gates.

Development evidence: the DING RPM built successfully; 53 native GNOME profile
checks and 45 command checks passed. Welcome passed 96 real WebKit scenarios and
12 layout checks. The desktop fixture passed 10 checks including the real GTK
switch, extension lifecycle, profile persistence, failure rollback and intact
files in a disposable HOME. This is not full ISO or drag-and-drop qualification.

Rollback: disable Active desktop in Vega, or remove DING using the package
manager; neither action moves Desktop files. Select the previous profile to
restore its saved layout. Revert the image package/default entries and minimum
requirements together if abandoning this candidate. These changes do not modify
kernel/NVIDIA policy, GRUB or user documents.
