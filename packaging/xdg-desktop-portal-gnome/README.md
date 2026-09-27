# GNOME global-shortcut success-response backport

Staging RPM candidate for [#125](https://github.com/lyra-os-linux/lyraos-desktop/issues/125).
The native consent dialog succeeds, but the Leap 16.1 package can report an error
because the success response is uninitialized. Apply only GNOME commit
`54087ebf0b467b4193f1b40f3177f55d415eaa9c` to the exact signed SUSE 48.0 source.
Do not upgrade GNOME or broaden the supervised account's permissions.

`sources.json` identifies the source RPM, its signature, the two source archives
and the upstream patch by SHA-256. The original SUSE spec is preserved except
for the release suffix, patch declaration, explicit `zstd` build dependency and
changelog. Source archives remain in the signed SRPM instead of being duplicated
in Git.

## Build in a disposable Leap 16.1 environment

Download the SRPM at `portal_gnome.url` in `sources.json`. Verify its SHA-256
and `rpm -K` against the already trusted SUSE signing key; reject NOKEY or a
signature failure. Create an empty RPM build tree and install the SRPM there:

```sh
rpm -i --define '_topdir /path/to/rpmbuild' /path/to/original.src.rpm
```

Copy this directory's spec to `rpmbuild/SPECS` and the patch to
`rpmbuild/SOURCES`. For direct rpmbuild outside OBS, replace `<CI_CNT>` and
`<B_CNT>` with `0` in that disposable spec copy. Install the build requirements from
the official Leap repository, then build with dependency checks enabled:

```sh
rpmbuild -ba --define '_topdir /path/to/rpmbuild' \
  /path/to/rpmbuild/SPECS/xdg-desktop-portal-gnome.spec
```

The local candidate release `160100.2.1.lyra1` sorts after the affected
`160100.2.1` and before a subsequent SUSE `160100.2.2`. It does not use an epoch
or a package lock. The OBS recipe uses `160100.2.1.lyra1.<CI_CNT>.<B_CNT>` to
preserve that ordering while incrementing source/build counters. Without this template,
OBS replaced the release with `lp161.160100.1`, below the affected SUSE package.
OBS/osc builds expand these placeholders automatically.
The language and debug subpackages retain upstream packaging.
The normal RPM dependency, scriptlet and file-conflict checks must remain enabled.

The historical local GCC 15.3 build added the automatic
`libc.so.6(GLIBC_2.38)(64bit)` requirement; the tested Leap 16.1 supplies glibc
2.40. The signed OBS build uses GCC 13.4 and has the same runtime requirements
as the SUSE original. Recheck requirements when qualifying another artifact.

## Delivery gate

The package is declared in `staging_only_packages`. It must pass the staging
build gate, and cannot be promoted until a reviewed manifest change grants
release ownership. This does not change repository priority or select it in KIWI.
The [signed staging qualification](../../docs/evidence/portal-staging/README.md)
passed main/language installation, upgrade, rollback and native tests in both
account types. Normal zypper updates, including the vegad repository update
path, do not cross from the SUSE vendor to this candidate. A package-specific
migration and return-to-SUSE policy still need review and execution tests;
do not globally relax vendor stickiness or change repository priorities.
Prefer an official fixed SUSE package when one is available.

Before closing #125: resolve that delivery policy, review promotion, then
validate the exact candidate ISO checksum. Historical local evidence remains
in `docs/evidence/portal-rpm/`. Parental-control production enablement remains a
separate incomplete item.
