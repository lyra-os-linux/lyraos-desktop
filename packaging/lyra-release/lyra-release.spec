Name:           lyra-release
Version:        1.0
Release:        0
Summary:        Updatable Lyra OS product identity
License:        GPL-3.0-only
URL:            https://github.com/lyra-os-linux/lyraos-desktop
Source0:        lyra-product-release
BuildArch:      noarch

%description
Owns the minimal product identity used to authorize and verify Lyra OS release
upgrades. Image-specific build and artifact metadata remain separate.

%prep

%build

%install
install -Dm0644 %{SOURCE0} \
    %{buildroot}%{_prefix}/lib/lyra-os/product-release

%check
grep -Fx "LYRA_VERSION_ID='%{version}'" %{SOURCE0}
grep -Fx "LYRA_EDITION='desktop'" %{SOURCE0}
grep -Fx "LYRA_ARCHITECTURE='x86_64'" %{SOURCE0}

%files
%dir %{_prefix}/lib/lyra-os
%{_prefix}/lib/lyra-os/product-release
