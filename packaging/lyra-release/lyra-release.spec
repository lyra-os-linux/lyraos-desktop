Name:           lyra-release
Version:        16.1
Release:        0
Summary:        Updatable Lyra OS product identity
License:        GPL-3.0-only
URL:            https://github.com/lyra-os-linux/lyraos-desktop
Source0:        lyra-product-release
Source1:        lyra-release-identity
Requires:       python3-base
# Only wheel may sudo with its own password; see %posttrans.
Requires:       sudo-policy-wheel-auth-self
Requires(posttrans): diffutils
BuildArch:      noarch

%description
Owns the minimal product identity used to authorize and verify Lyra OS release
upgrades and reapplies the Lyra display identity after base release updates.
Image-specific build and artifact metadata remain separate.

%prep

%build

%install
install -Dm0644 %{SOURCE0} \
    %{buildroot}%{_prefix}/lib/lyra-os/product-release

install -Dm0755 %{SOURCE1} %{buildroot}%{_libexecdir}/lyra-release-identity

%check
grep -Fx "LYRA_VERSION_ID='%{version}'" %{SOURCE0}
grep -Fx "LYRA_EDITION='desktop'" %{SOURCE0}
grep -Fx "LYRA_ARCHITECTURE='x86_64'" %{SOURCE0}
grep -Fx "LYRA_BUILD_ID='lyra-release-%{version}'" %{SOURCE0}

%posttrans
%{_libexecdir}/lyra-release-identity
# Lyra installers up to 16.1 RC 2 wrote this file with a global
# "Defaults !targetpw", which let every account sudo with its own password.
# sudo-policy-wheel-auth-self scopes that to wheel. Remove the file only when
# it is still exactly what the installer wrote and the vendor sudoers, which
# includes the policy, is the one in use.
installer_sudoers=/etc/sudoers.d/10-installer
if [ -f "$installer_sudoers" ]; then
    if [ ! -e /etc/sudoers ] && [ -f /usr/etc/sudoers.d/50-wheel-auth-self ] &&
       printf '%%s\n' 'Defaults !targetpw' '%%wheel ALL=(ALL) ALL' | cmp -s - "$installer_sudoers"; then
        rm -f "$installer_sudoers"
    elif grep -qE '^Defaults[[:space:]]+!targetpw' "$installer_sudoers"; then
        echo "lyra-release: $installer_sudoers still disables targetpw for every account; review it" >&2
    fi
fi

# Reapply after release-file transactions, using RPM default trigger priority.
%transfiletriggerin -- /usr/lib /etc
while IFS= read -r changed_path; do
    case "$changed_path" in
        /usr/lib/os-release|/etc/os-release)
            %{_libexecdir}/lyra-release-identity
            exit $?
            ;;
    esac
done

%preun
if [ "$1" -eq 0 ]; then
    %{_libexecdir}/lyra-release-identity --restore || :
fi

%files
%dir %{_prefix}/lib/lyra-os
%{_prefix}/lib/lyra-os/product-release

%{_libexecdir}/lyra-release-identity
