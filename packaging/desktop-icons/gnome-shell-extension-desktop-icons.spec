# DING upstream release qualified for Lyra's GNOME 48 image.
Name:           gnome-shell-extension-desktop-icons
Version:        49.0.5
Release:        0
Summary:        Desktop files and icons for GNOME Shell
License:        GPL-3.0-or-later
URL:            https://gitlab.com/rastersoft/desktop-icons-ng
# Upstream tag 49.0.5, commit c32667693d0831c29e3ab3f7bfeb675ea1531a00.
Source0:        desktop-icons-ng-%{version}.tar.gz
BuildArch:      noarch
BuildRequires:  meson
BuildRequires:  ninja
BuildRequires:  gettext-tools
BuildRequires:  glib2-devel
BuildRequires:  python3
Requires:       gnome-shell >= 46
Requires:       gnome-shell < 50
Requires:       nautilus >= 45
Requires:       gjs
Requires:       typelib(Adw)
Requires:       typelib(GdkX11) = 3.0
Requires:       typelib(GnomeDesktop) = 3.0
Requires:       typelib(GnomeAutoar)
Requires:       typelib(Gtk) = 3.0

%description
Desktop Icons NG displays files, folders, mounted drives and Trash on the
GNOME desktop, including drag and drop with Files. This is the upstream DING
extension packaged for GNOME 48. Desktop files remain in the user's normal
Desktop directory when icons are disabled through Vega.

%prep
%autosetup -n desktop-icons-ng-%{version}

%build
%meson
%meson_build

%install
%meson_install
# Ship a private schema as well, so isolated sessions and extension preferences
# resolve the same schema without depending on the global compiled cache.
install -Dm644 schemas/org.gnome.shell.extensions.ding.gschema.xml \
  %{buildroot}%{_datadir}/gnome-shell/extensions/ding@rastersoft.com/schemas/org.gnome.shell.extensions.ding.gschema.xml
glib-compile-schemas %{buildroot}%{_datadir}/gnome-shell/extensions/ding@rastersoft.com/schemas
%find_lang ding

%check
python3 -c 'import json; assert "48" in json.load(open("metadata.json"))["shell-version"]'
glib-compile-schemas --strict --dry-run schemas

%files -f ding.lang
%license COPYING
%doc README.md HISTORY.md
%dir %{_datadir}/gnome-shell
%dir %{_datadir}/gnome-shell/extensions
%{_datadir}/gnome-shell/extensions/ding@rastersoft.com
%{_datadir}/glib-2.0/schemas/org.gnome.shell.extensions.ding.gschema.xml
%config(noreplace) %{_sysconfdir}/apparmor.d/desktop-icons-ng

%changelog
