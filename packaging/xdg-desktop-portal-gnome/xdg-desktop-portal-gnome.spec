#
# spec file for package xdg-desktop-portal-gnome
#
# Copyright (c) 2025 SUSE LLC
#
# All modifications and additions to the file contributed by third parties
# remain the property of their copyright owners, unless otherwise agreed
# upon. The license for this file, and modifications and additions to the
# file, is the same license as for the pristine package itself (unless the
# license for the pristine package is not an Open Source License, in which
# case the license is the MIT License). An "Open Source License" is a
# license that conforms to the Open Source Definition (Version 1.9)
# published by the Open Source Initiative.

# Please submit bugfixes or comments via https://bugs.opensuse.org/
#


Name:           xdg-desktop-portal-gnome
VCS: https://src.suse.de/pool/xdg-desktop-portal-gnome?trackingbranch=slfo-1.3#708df855464e1720e1b78f1c99dacb919d3be3f720660253a54cf3fa6f6efd00
Version:        48.0
Release:        160100.2.1.lyra1
Summary:        A backend implementation for xdg-desktop-portal
License:        LGPL-2.1-or-later
URL:            https://gitlab.gnome.org/GNOME/xdg-desktop-portal-gnome
Source:         %{name}-%{version}.tar.zst
Source1:        libgxdp-0.gitmodule.tar.zst
# GNOME MR223, upstream commit 54087ebf0b467b4193f1b40f3177f55d415eaa9c
Patch0:         globalshortcuts-success.patch

BuildRequires:  c_compiler
BuildRequires:  fontconfig
BuildRequires:  meson
BuildRequires:  pkgconfig
BuildRequires:  xdg-desktop-portal-gtk
BuildRequires:  pkgconfig(dbus-1)
BuildRequires:  pkgconfig(gio-unix-2.0)
BuildRequires:  pkgconfig(glib-2.0) >= 2.44
BuildRequires:  pkgconfig(gnome-desktop-4)
BuildRequires:  pkgconfig(gsettings-desktop-schemas) >= 47.alpha
BuildRequires:  pkgconfig(gtk4) >= 4.0
BuildRequires:  pkgconfig(libadwaita-1)
BuildRequires:  pkgconfig(systemd)
BuildRequires:  pkgconfig(xdg-desktop-portal) >= 1.19.1
Requires:       xdg-desktop-portal
# Use rich deps to pull in this package when gnome-shell and flatpak (or snapd) are both installed
Supplements:    (gnome-shell and (flatpak or snapd))

%description
A backend implementation for xdg-desktop-portal for the GNOME
desktop environment.

%lang_package

%prep
%autosetup -p1
pushd subprojects
tar xf %{SOURCE1}
mv libgxdp-0.gitmodule libgxdp
popd

%build
%meson \
	%{nil}
%meson_build

%install
%meson_install
%find_lang %{name}

%post
%systemd_user_post %{name}.service

%preun
%systemd_user_preun %{name}.service

%files
%license COPYING
%doc README.md NEWS
%{_userunitdir}/xdg-desktop-portal-gnome.service
%{_libexecdir}/xdg-desktop-portal-gnome
%{_datadir}/applications/xdg-desktop-portal-gnome.desktop
%{_datadir}/dbus-1/services/org.freedesktop.impl.portal.desktop.gnome.service
%{_datadir}/glib-2.0/schemas/xdg-desktop-portal-gnome.gschema.xml
%{_datadir}/xdg-desktop-portal/portals/gnome.portal

%files lang -f %{name}.lang

%changelog
* Sun Sep 27 2026 Lyra OS <https://github.com/lyra-os-linux>
- Backport upstream success-response initialization for global shortcuts.
  Fixes consent returning an error after successful registration (#125).
  Preserve the SUSE 48.0 sources, submodule and packaging behavior.
* Fri Mar 28 2025 alynx.zhou@suse.com
- Bump libgxdp commit to e68375c7ace to fix initialization under
  X11. (bsc#1240057)
* Mon Mar 17 2025 dimstar@opensuse.org
- Update to version 48.0:
  + Updated translations.
* Sat Mar  1 2025 bjorn.lie@gmail.com
- Update to version 48.rc:
  + Add global shortcuts portal backend.
* Mon Feb 17 2025 bjorn.lie@gmail.com
- Update to version 48.beta.2:
  + Add USB portal backend
  + Fix screen cast portal done signal emission
  + Use the new AdwInlineViewSwitcher widget in the screencast
    dialog
  + Update apps list properly in the screencast dialog
  + Generate systemd sysexts in CI
  + Fix an issue with the Notification portal implementation
  + Depend on libadwaita >= 1.7.alpha
  + Updated translations.
- Drop notification-Add-missing-GUnixFDList-argument.patch: Fixed
  upstream.
* Mon Feb 17 2025 bjorn.lie@gmail.com
- Update to version 48.alpha:
  + Outsource external window management to libgxdp
  + Fix memory leak in screencast widget
  + Implement a signal handler to help with ASAN
  + Use Adwaita widgets in the app chooser dialog
  + Fix a memory management issue with the screencast widget
  + Depend on xdg-desktop-portal >= 1.19.1
  + Updated translations.
- Add new sub-module to service and spec.
- Drop notification-null-icon-pointer.patch: fixed upstream.
* Mon Feb 17 2025 bjorn.lie@gmail.com
- Update to version 47.3:
  + Fix build against xdg-desktop-portal >= 1.19.1
  + Fix initialization of X11 display.
- Drop patches fixed upstream:
  + notification-Add-missing-GUnixFDList-argument.patch
  + notification-null-icon-pointer.patch
* Mon Feb 10 2025 taaem@mailbox.org
- Add notification-Add-missing-GUnixFDList-argument.patch
  * Fix crash on notification (bsc#1236435)
    glgo#GNOME/xdg-desktop-portal-gnome#157
    glgo#GNOME/xdg-desktop-portal-gnome!210
* Mon Jan 20 2025 bjorn.lie@gmail.com
- Update to version 47.2:
  + More resilience against GNOME Shell errors
  + Fix memory leak in screencast widget
  + Avoid a GTK portal recursion, and a 25 second delay in startup
- Drop xdg-desktop-portal-gnome-gtk_init.patch: Fixed upstream.
* Thu Jan  9 2025 pallaswept@proton.me
- Add notification-null-icon-pointer.patch
  * Fixes build against xdg-desktop-portal 1.19.1
* Fri Dec 20 2024 bjorn.lie@gmail.com
- Update to version 47.1+3:
  * display-state-tracker: Use proxy from source object in callback
  * Updated translations.
* Fri Dec 20 2024 dimstar@opensuse.org
- Add xdg-desktop-portal-gnome-gtk_init.patch: Call gtk_init before
  opening a display.
* Thu Sep 19 2024 bjorn.lie@gmail.com
- Update to version 47.1:
  + Fix the capabilities for the print dialog.
* Mon Sep 16 2024 dimstar@opensuse.org
- Update to version 47.0:
  + Updated translations.
* Mon Sep  2 2024 bjorn.lie@gmail.com
- Update to version 47.rc:
  + Fix restoring last used folder in the File Chooser portal
  + Fix selecting multiple window on single selection
  + Do not block xdg-desktop-portal-gnome when connecting to
    Nautilus
  + Fix incorrectly set mimetype in the File Chooser portal
  + Updated tanslations.
* Sun Aug 25 2024 bjorn.lie@gmail.com
- Update to version 47.beta:
  + Use GNOME Shell's private API for the Notification portal
  + Use Nautilus for the File Chooser portal
  + Updated translations.
- Changes from version 47.alpha:
  + Expose the new accent colors setting
  + Various cleanups to the screencast widget
  + Add support for the "supported_output_file_formats" option in
    the Print portal
  + Fix default layout mode of the ScreenCast/Remote Desktop portal
  + Updated translations.
* Mon May 27 2024 dimstar@opensuse.org
- Update to version 46.2:
  + Various behavioral and accessibility fixes to the ScreenCast
    portal dialog.
  + Updated translations.
* Wed May  1 2024 dimstar@opensuse.org
- Update to version 46.1:
  + Remove D-Bus call timeout from Access portal requests that are
    proxied to GNOME Shell. This prevents the Access portal from
    failing requests if the user doesn't click on a dialog for more
    than 25 seconds.
  + Various fixes to the ScreenCast portal dialog.
  + Updated translations.
* Mon Mar 18 2024 dimstar@opensuse.org
- Update to version 46.0:
  + Updated translations.
* Tue Mar  5 2024 dimstar@opensuse.org
- Update to version 46.rc:
  + Updated translations.
* Tue Feb 13 2024 dimstar@opensuse.org
- Update to version 46.beta:
  + Depend on xdg-desktop-portal 1.18.2.
  + Use modern Adwaita widgets thoroughly.
  + Expose the org.gnome.desktop.calendar schema through the
    Settings portal.
  + Put all dialogs in separate window groups so they don't block
    each other.
  + Plug several memory leaks.
  + Redesign the screencast screen picker.
  + Updated translations.
* Sun Nov 26 2023 bjorn.lie@gmail.com
- Update to version 45.1:
  + accountdialog: Fix crash when pressing Escape
  + Send remote file URIs as local FUSE URIs
  + Various fixes to screencast and input capture
  + Expose org.gnome.desktop.calendar through the Settings portal
  + Put dialogs in separate window groups
  + Updated translations.
* Mon Sep 18 2023 bjorn.lie@gmail.com
- Update to version 45.0:
  + Improve build system detection of libadwaita.
  + Updated translations.
* Mon Sep  4 2023 bjorn.lie@gmail.com
- Update to version 45.rc:
  + Advertise the version of the ScreenCast portal correctly.
  + Proxy the 'mapping_id' property to xdg-desktop-portal.
  + Updated translations.
* Sat Aug  5 2023 bjorn.lie@gmail.com
- Update to version 45.beta:
  + Implement the Input Capture portal
  + Implement the Clipboard portal
  + Implement restoration of remote desktop sessions
  + Remote desktop: add the ability to communicate via an EIS
    socket
  + Updated translations.
* Mon Jul 31 2023 bjorn.lie@gmail.com
- Update to version 45.alpha:
  + Support setting current folder in the file chooser's OpenFile
    method.
  + Ensure wallpaper is set with a valid URI.
  + Use provided accept label in Printer dialog.
  + Generate the gnome.portal file.
  + Updated translations.
* Mon Jul 31 2023 bjorn.lie@gmail.com
- Update to version 44.2:
  + Expose settings backend when running outside of GNOME.
  + Updated translations.
* Fri Apr 21 2023 bjorn.lie@gmail.com
- Update to version 44.1:
  + Improve handling of non-existing files on the filechooser
    portal
  + Minor debugging improvements to the backgrounds portal
  + More precise initialization timing
  + Fix duplicate monitor and window streams
  + Updated translations.
* Mon Mar 20 2023 bjorn.lie@gmail.com
- Update to version 44.0:
  + Updated translations.
* Tue Mar  7 2023 bjorn.lie@gmail.com
- Update to version 44.rc:
  + Grant restore permission to transient mode by default
  + Updated translations.
* Fri Feb 24 2023 bjorn.lie@gmail.com
- Update to version 44.beta:
  + Act as a service channel for portals for Mutter.
  + Updated translations.
* Tue Oct 18 2022 bjorn.lie@gmail.com
- Update to version 43.1:
  + Close dialogs with the Escape key.
  + Updated translations.
* Thu Sep 15 2022 bjorn.lie@gmail.com
- Update to version 43.0:
  + Updated translations.
* Sun Sep  4 2022 bjorn.lie@gmail.com
- Update to version 43.rc:
  + Remember last app folder in the Filechooser portal
  + Improve Closed signal emission in the RemoteDesktop/Screencast
    portal
  + Updated translations.
* Fri Aug 12 2022 dimstar@opensuse.org
- Update to version 43.beta:
  + Don't show screenshot sharing dialog for non-interactive
    screenshots.
  + Fix restoring window screencast streams.
  + Updated translations.
* Sun Jul 17 2022 bjorn.lie@gmail.com
- Update to version 43.alpha:
  + Various fixes to the screencast dialog.
  + New Dynamic Launcher portal.
  + Plug various memory leaks.
  + Tweak wallpaper portal dialog.
  + Updated translations.
* Sun Jul  3 2022 bjorn.lie@gmail.com
- Update to version 42.3:
  + Backport screencast session fixes.
- Changes from version 42.2:
  + Fix invalid usage of app chooder dialog after its destruction.
  + Properly handle errors from file operations.
  + Fix various memory leaks.
  + Updated translations.
* Wed Apr 27 2022 dimstar@opensuse.org
- Update to version 42.1:
  + Improve filechooser handling of file names and paths.
  + Updated translations.
* Fri Mar 18 2022 bjorn.lie@gmail.com
- Update to version 42.0.1:
  + Adapt to xdg-desktop-portal screencast restore changes.
  + Don't send selection on remote desktop when nothing was
    selected.
  + Minor cleanups.
* Fri Mar 18 2022 bjorn.lie@gmail.com
- Update to version 42.0:
  + Updated translations.
* Tue Mar  8 2022 bjorn.lie@gmail.com
- Update to version 42.rc:
  + Support dark style preference.
  + Support virtual screen cast sources.
  + Redesign screencast portal window.
  + Implement screencast restoration.
  + Use libgnome-desktop-4 for wallpapers.
  + Implement Account portal.
  + Implement Print portal.
- Add pkgconfig(libadwaita-1) and pkgconfig(gnome-desktop-4)
  BuildRequires: New dependencies.
* Fri Oct  1 2021 bjorn.lie@gmail.com
- Add missing xdg-desktop-portal Requires and (gnome-shell and
  (flatpak or snapd)) Supplements, autoinstall when both are
  installed.
* Sat Sep 25 2021 bjorn.lie@gmail.com
- Update to version 41.1:
  + Force the cairo renderer to avoid a crash.
* Sat Sep 18 2021 bjorn.lie@gmail.com
- Initial package for openSUSE, version 41.0
