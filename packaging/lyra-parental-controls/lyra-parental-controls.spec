Name:           lyra-parental-controls
Version:        0.1.0
Release:        0
Summary:        Supervised accounts for Lyra OS basic parental controls
License:        GPL-3.0-only
URL:            https://github.com/lyra-os-linux/lyraos-desktop
Source0:        lyra-parental-controls.sysusers
Source1:        50-lyra-supervised.conf
BuildRequires:  openssh-clients
BuildRequires:  openssh-server
BuildRequires:  sysuser-tools
Requires:       openssh-server
%{?sysusers_requires}
BuildArch:      noarch

%description
Marks accounts supervised by Lyra OS basic parental controls through the
lyra-supervised system group. Members of the group cannot log in over SSH.
The rules themselves (applications, installation, age rating) belong to
malcontent and its "Controle parental" application.

%prep

%build
%sysusers_generate_pre %{SOURCE0} %{name} %{name}.conf

%install
install -Dm0644 %{SOURCE0} %{buildroot}%{_sysusersdir}/%{name}.conf
install -Dm0644 %{SOURCE1} %{buildroot}%{_distconfdir}/ssh/sshd_config.d/50-lyra-supervised.conf

%check
grep -Fx 'g lyra-supervised -' %{SOURCE0}
grep -Fx 'DenyGroups lyra-supervised' %{SOURCE1}
# sshd must parse the drop-in and apply DenyGroups.
ssh-keygen -q -t ed25519 -N '' -f check-hostkey
printf 'Include %s\n' %{buildroot}%{_distconfdir}/ssh/sshd_config.d/50-lyra-supervised.conf > check-sshd_config
/usr/sbin/sshd -T -f check-sshd_config -h "$PWD/check-hostkey" | grep -Fx 'denygroups lyra-supervised'

%pre -f %{name}.pre

# sshd keeps the configuration it loaded at start; reload only if running.
%post
systemctl try-reload-or-restart sshd.service >/dev/null 2>&1 || :

%postun
systemctl try-reload-or-restart sshd.service >/dev/null 2>&1 || :

%files
%{_sysusersdir}/%{name}.conf
%dir %{_distconfdir}/ssh
%dir %{_distconfdir}/ssh/sshd_config.d
%{_distconfdir}/ssh/sshd_config.d/50-lyra-supervised.conf

%changelog
