Name:           lyra-parental-controls
Version:        0.1.0
Release:        0
Summary:        Supervised accounts for Lyra OS basic parental controls
License:        GPL-3.0-only
URL:            https://github.com/lyra-os-linux/lyraos-desktop
Source0:        lyra-parental-controls.sysusers
Source1:        50-lyra-supervised.conf
Source2:        login
Source3:        access.conf
Source4:        dconf-profile
Source5:        00-lyra-supervised
Source6:        00-lyra-supervised.locks
Source7:        60-lyra-supervised.envgen
Source8:        52-lyra-parental-read.rules
BuildRequires:  openssh-clients
BuildRequires:  openssh-server
BuildRequires:  sysuser-tools
# Vendor /usr/lib/pam.d/login, compared in %check.
BuildRequires:  util-linux
Requires:       openssh-server
Requires:       pam
Requires:       util-linux
Requires:       dconf
# The parental controls app and its read rule come with this package, so
# installs made before they were in the image get them through zypper.
Requires:       malcontent
Requires:       malcontent-control
Requires:       typelib-1_0-MalcontentUi-1
Requires:       polkit
Requires:       systemd
%{?sysusers_requires}
BuildArch:      noarch

%description
Marks accounts supervised by Lyra OS basic parental controls through the
lyra-supervised system group. Members of the group cannot log in over SSH or
on a text console (TTY); the graphical login is unchanged. Their GNOME
session uses a dconf profile that locks the Alt+F2 command line. Brings the
"Controle parental" application and a polkit rule that lets administrators
read the restrictions without a password, as upstream malcontent does.
The rules themselves (applications, installation, age rating) belong to
malcontent and its "Controle parental" application.

%prep

%build
%sysusers_generate_pre %{SOURCE0} %{name} %{name}.conf

%install
install -Dm0644 %{SOURCE0} %{buildroot}%{_sysusersdir}/%{name}.conf
install -Dm0644 %{SOURCE1} %{buildroot}%{_distconfdir}/ssh/sshd_config.d/50-lyra-supervised.conf
# Leap ships login only in /usr/lib/pam.d; this copy in /etc shadows it to add
# pam_access for the login (TTY) service alone. A pam_access rule in the common
# stack would also block GDM, whose PAM_TTY is a VT too.
install -Dm0644 %{SOURCE2} %{buildroot}%{_sysconfdir}/pam.d/login
install -Dm0644 %{SOURCE3} %{buildroot}%{_datadir}/%{name}/access.conf
# GNOME session of supervised accounts: own dconf profile, chosen by a
# systemd user environment generator only for members of the group.
install -Dm0644 %{SOURCE4} %{buildroot}%{_sysconfdir}/dconf/profile/lyra-supervised
install -Dm0644 %{SOURCE5} %{buildroot}%{_sysconfdir}/dconf/db/lyra-supervised.d/00-lyra-supervised
install -Dm0644 %{SOURCE6} %{buildroot}%{_sysconfdir}/dconf/db/lyra-supervised.d/locks/00-lyra-supervised
install -Dm0755 %{SOURCE7} %{buildroot}%{_prefix}/lib/systemd/user-environment-generators/60-lyra-supervised
install -Dm0644 %{SOURCE8} %{buildroot}%{_datadir}/polkit-1/rules.d/52-lyra-parental-read.rules

%check
# The copy must stay the vendor file plus one line. When util-linux changes
# /usr/lib/pam.d/login, this fails and the copy has to be refreshed.
grep -vFx 'account   required   pam_access.so accessfile=%{_datadir}/%{name}/access.conf' %{SOURCE2} \
    | diff -u %{_prefix}/lib/pam.d/login -
test "$(grep -c pam_access %{SOURCE2})" = 1
grep -Fx -- '-:(lyra-supervised):ALL' %{SOURCE3}
grep -Fx 'g lyra-supervised -' %{SOURCE0}
grep -Fx 'DenyGroups lyra-supervised' %{SOURCE1}
grep -Fx 'system-db:lyra-supervised' %{SOURCE4}
grep -Fx 'disable-command-line=true' %{SOURCE5}
grep -Fx '/org/gnome/desktop/lockdown/disable-command-line' %{SOURCE6}
sh -n %{SOURCE7}
grep -F 'subject.isInGroup("wheel")' %{SOURCE8}
! grep -E 'Change(Own|Any)' %{SOURCE8}
# sshd must parse the drop-in and apply DenyGroups.
ssh-keygen -q -t ed25519 -N '' -f check-hostkey
printf 'Include %s\n' %{buildroot}%{_distconfdir}/ssh/sshd_config.d/50-lyra-supervised.conf > check-sshd_config
/usr/sbin/sshd -T -f check-sshd_config -h "$PWD/check-hostkey" | grep -Fx 'denygroups lyra-supervised'

%pre -f %{name}.pre

# sshd keeps the configuration it loaded at start; reload only if running.
%post
systemctl try-reload-or-restart sshd.service >/dev/null 2>&1 || :
dconf update >/dev/null 2>&1 || :

%postun
systemctl try-reload-or-restart sshd.service >/dev/null 2>&1 || :
dconf update >/dev/null 2>&1 || :

%files
%{_sysusersdir}/%{name}.conf
%dir %{_distconfdir}/ssh
%dir %{_distconfdir}/ssh/sshd_config.d
%{_distconfdir}/ssh/sshd_config.d/50-lyra-supervised.conf
%config %{_sysconfdir}/pam.d/login
%{_datadir}/%{name}
%dir %{_sysconfdir}/dconf
%dir %{_sysconfdir}/dconf/profile
%dir %{_sysconfdir}/dconf/db
%{_sysconfdir}/dconf/profile/lyra-supervised
%{_sysconfdir}/dconf/db/lyra-supervised.d
%ghost %{_sysconfdir}/dconf/db/lyra-supervised
%dir %{_prefix}/lib/systemd/user-environment-generators
%{_prefix}/lib/systemd/user-environment-generators/60-lyra-supervised
%dir %{_datadir}/polkit-1
%dir %{_datadir}/polkit-1/rules.d
%{_datadir}/polkit-1/rules.d/52-lyra-parental-read.rules

%changelog
