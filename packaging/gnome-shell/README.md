# GNOME Shell libgvc NULL active-profile fix

Staging RPM candidate for SHELL-01 in [`docs/iso-fix-tracker.md`](../../docs/iso-fix-tracker.md).
On 2026-11-02 the physical station's `gnome-shell` 48.8-160100.2.1 crashed
with SIGSEGV three seconds after login. `pipewire-pulse` announced a USB webcam
card before its profiles were known (`card 52 port 0 profiles inconsistent
(0 < 1)`), so `pa_card_info.active_profile` was NULL. The bundled
libgnome-volume-control then executed
`gvc_mixer_card_set_profile (card, info->active_profile->name)` in
`update_card()`; the core shows the faulting `mov (%rax),%rsi` with `rax = 0`
immediately before that call. libgnome-volume-control master `0a4eda0` still
has the unchecked dereference.

The trigger is a PipeWire enumeration race, not one webcam model: any card
announced with zero profiles can hit it. Do not ship a WirePlumber rule that
disables specific devices instead.

`gnome-shell-gvc-null-active-profile.patch` only guards the two
`info->active_profile` reads in `update_card()`. With zero profiles
`gvc_mixer_card_set_profile()` already refuses to run
(`card->priv->profiles != NULL`), so skipping the call keeps the existing
state; the next card update with profiles selects the active one. Shell JS
does not call `gvc_mixer_ui_device_get_active_profile()`. Do not upgrade
GNOME or carry other changes in this package.

`sources.json` identifies the source RPM, its signature, every source archive
and patch by SHA-256. The original SUSE spec is preserved except for the
release suffix, the `Patch200` declaration and the changelog. `gnome-shell.changes`
is the spec changelog converted to OBS format. Source archives remain in the
signed SRPM instead of being duplicated in Git.

## Build in a disposable Leap 16.1 environment

Download the SRPM at `gnome_shell.url` in `sources.json`. Verify its SHA-256
and `rpm -K` against the already trusted SUSE signing key; reject NOKEY or a
signature failure. Install it in an empty RPM build tree, copy this
directory's spec and patch over it and, for direct rpmbuild outside OBS,
replace `<CI_CNT>` and `<B_CNT>` with `0` in that disposable spec copy. Build
with dependency checks enabled. The patch was verified to apply after the SUSE
`%autopatch -M 999` set; the build itself has not run yet.

The release `160100.2.1.lyra1.<CI_CNT>.<B_CNT>` sorts after the affected SUSE
`160100.2.1` and before a subsequent `160100.2.2`, without epoch or lock. All
subpackages (`gnome-shell`, `-lang`, `-calendar`, `-devel`, `gnome-extensions`)
come from this one spec and must move together.

## Delivery gate

Not yet declared in `obs/projects.toml`: `obs-release.py check` requires
every `staging_only_packages` entry to build in staging, so add it in the same
change that uploads this source to staging. Delivery to installed systems follows the
[package-scoped migration policy](../../docs/portal-package-delivery.md):
signed Updater `PackageMigration` manifest with exact artifact identities,
no global vendor change, no repository priority change. Unlike the portal,
`gnome-shell` runs the user session, so the transition must be applied
offline and qualified with a live desktop; never replace it under a running
session.

Before closing SHELL-01: OBS staging build and signature, regression of
audio, volume OSD, quick settings output/input selection and USB hotplug on
the patched build, the migration and its rollback, then the exact candidate
ISO checksum. Report the defect upstream to libgnome-volume-control and
prefer an official fixed SUSE package when one is available.
