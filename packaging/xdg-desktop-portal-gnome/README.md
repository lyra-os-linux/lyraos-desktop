# GNOME global-shortcut success-response backport

Local RPM candidate for [#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125).
The native consent dialog succeeds, but the Leap 16.1 package can report an error
because the success response is uninitialized. Apply only GNOME commit
`54087ebf0b467b4193f1b40f3177f55d415eaa9c` to the exact signed SUSE 48.0 source.
Do not upgrade GNOME or broaden the supervised account's permissions.

`sources.json` identifies the source RPM, its signature, the two source archives
and the upstream patch by SHA-256. The original SUSE spec is preserved except
for the release suffix, patch declaration and changelog. Source archives remain
in the signed SRPM instead of being duplicated in Git.

## Build in a disposable Leap 16.1 environment

Download the SRPM at `portal_gnome.url` in `sources.json`. Verify its SHA-256
and `rpm -K` against the already trusted SUSE signing key; reject NOKEY or a
signature failure. Create an empty RPM build tree and install the SRPM there:

```sh
rpm -i --define '_topdir /path/to/rpmbuild' /path/to/original.src.rpm
```

Copy this directory's spec to `rpmbuild/SPECS` and the patch to
`rpmbuild/SOURCES`. Install the build requirements declared by the spec from
the official Leap repository, then build with dependency checks enabled:

```sh
rpmbuild -ba --define '_topdir /path/to/rpmbuild' \
  /path/to/rpmbuild/SPECS/xdg-desktop-portal-gnome.spec
```

The candidate release `160100.2.1.lyra1` sorts after the affected
`160100.2.1` and before a subsequent SUSE `160100.2.2`. It does not use an epoch
or a package lock. The language and debug subpackages retain upstream packaging.
The normal RPM dependency, scriptlet and file-conflict checks must remain enabled.

The local build uses Leap's GCC 15.3 default C dialect. Its automatic dependencies
add `libc.so.6(GLIBC_2.38)(64bit)` through `__isoc23_strtol`; the tested Leap 16.1
base supplies glibc 2.40. No declared build/runtime dependency was changed. This
candidate is qualified for Leap 16.1 only; compare the final OBS artifact's
requirements again.

## Delivery gate

This directory does **not** add a package to OBS, change repository priority or
select the backport in KIWI. A local unsigned RPM qualifies the patch and RPM
lifecycle only. The staged, signed artifact must be tested again by checksum
before promotion. The installed-system policy gives official repositories
priority over third-party repositories: verify the actual solver and vendor
behavior for the signed release; do not silently pin or override that policy.
Prefer an official fixed SUSE package when one is available.

Before closing #125: stage and sign the package, qualify installation/upgrade/
rollback and both account types with that artifact, review the promotion, then
validate the exact candidate ISO checksum. Evidence for the local candidate is
in `docs/evidence/portal-rpm/`. Parental-control production enablement remains a
separate incomplete item.
