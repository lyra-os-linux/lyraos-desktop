Name:           lyra-release
Version:        1.1
Release:        0
Summary:        Updatable Lyra OS product identity
License:        GPL-3.0-only
URL:            https://github.com/lyra-os-linux/lyraos-desktop
Source0:        lyra-product-release
Source1:        lyra-release-identity
Requires:       python3-base
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

# Run after standard transaction scriptlets; no daemon or overlapping file owner.
%transfiletriggerin -P 1000 -- /usr/lib/os-release /etc/os-release
%{_libexecdir}/lyra-release-identity

%preun
if [ "$1" -eq 0 ]; then
    %{_libexecdir}/lyra-release-identity --restore || :
fi

%files
%dir %{_prefix}/lib/lyra-os
%{_prefix}/lib/lyra-os/product-release

%{_libexecdir}/lyra-release-identity
