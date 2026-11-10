Name:           lyra-display-wake
Version:        0.1.0
Release:        0
Summary:        Recover NVIDIA outputs that stay dark after display power saving
License:        GPL-3.0-only
URL:            https://github.com/lyra-os-linux/lyraos-desktop
Source0:        lyra-display-wake
Source1:        lyra-display-wake.service
Source2:        90-lyra-display-wake.preset
BuildRequires:  python3-base
BuildRequires:  systemd-rpm-macros
Requires:       python3-gobject
Requires:       typelib-1_0-Gio-2_0
# Installed on its own from the Lyra repository: nothing in the image or in
# lyra-release has to pull it in.
BuildArch:      noarch
%{?systemd_requires}

%description
Workaround for hybrid laptops where an output on the NVIDIA GPU stays dark
after GNOME turns the screens back on from power saving (DPMS), while the
kernel and Mutter report it as enabled. When the screens wake, a GNOME
session service switches each active NVIDIA output to another refresh rate
at the same resolution and back, which brings the signal back. The changes
are temporary: the saved monitor configuration is never written. Without the
nvidia_drm module the service does not start.

%prep

%build

%install
install -Dm0755 %{SOURCE0} %{buildroot}%{_libexecdir}/lyra-display-wake
install -Dm0644 %{SOURCE1} %{buildroot}%{_userunitdir}/lyra-display-wake.service
install -Dm0644 %{SOURCE2} %{buildroot}%{_userpresetdir}/90-lyra-display-wake.preset

%check
python3 -m py_compile %{SOURCE0}
grep -Fx 'ConditionPathExists=/sys/module/nvidia_drm' %{SOURCE1}
grep -Fx 'ExecStart=%{_libexecdir}/lyra-display-wake' %{SOURCE1}
grep -Fx 'enable lyra-display-wake.service' %{SOURCE2}

# %pre marks the new unit; without it %post does not apply the preset.
%pre
%systemd_user_pre lyra-display-wake.service

# Enables the unit for every user; it starts at the next GNOME login.
%post
%systemd_user_post lyra-display-wake.service

%preun
%systemd_user_preun lyra-display-wake.service

%postun
%systemd_user_postun lyra-display-wake.service

%files
%{_libexecdir}/lyra-display-wake
%{_userunitdir}/lyra-display-wake.service
%{_userpresetdir}/90-lyra-display-wake.preset

%changelog
