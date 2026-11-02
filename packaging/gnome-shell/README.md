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
with dependency checks enabled.

Staging revision 1 (2026-11-02) built as `48.8-160100.2.1.lyra1.160100.1`, signed
with the project key `58097F767EDCA82E`. SHA-256 of the binaries:

| RPM | SHA-256 |
| --- | --- |
| `gnome-shell` x86_64 | `04ce56d1dde144ecc8366189af0c5da3d83d0178b02e5ad16e8939673135232a` |
| `gnome-shell-lang` noarch | `984db4773d8f99a4cc40b3a8c88780498a58f7935a2d50ce008bf84f1ef9eada` |
| `gnome-shell-calendar` x86_64 | `fd02da91eec6e906f947742306e4b1cc9b61c617a624df5f01439150265e9734` |
| `gnome-extensions` x86_64 | `6d72398498861138b951e88fcf305cd7eab6cc00f329b3433c971be9330f8569` |
| `gnome-shell-devel` x86_64 | `47c0e0c530d248d51aa35e828f3698aa4310934d6909c519c4a46d3bc6a6895a` |

In the built `libgvc.so`, `_pa_context_get_card_info_by_index_cb` now tests
the active-profile pointer (`test %rax,%rax; je`) before
`gvc_mixer_card_set_profile`; the SUSE binary dereferenced it directly. The
three rpmlint errors (`no-binary` on `gnome-extensions`/`-devel`,
`branding-requires-unversioned gnome-themes-accessibility`) come from the
unchanged SUSE packaging, not from the patch. Runtime has not been tested yet.

The release `160100.2.1.lyra1.<CI_CNT>.<B_CNT>` sorts after the affected SUSE
`160100.2.1` and before a subsequent `160100.2.2`, without epoch or lock. All
subpackages (`gnome-shell`, `-lang`, `-calendar`, `-devel`, `gnome-extensions`)
come from this one spec and must move together.

## Delivery gate

Declared in `staging_only_packages` (staging revision 1). Delivery to installed systems follows the
[package-scoped migration policy](../../docs/portal-package-delivery.md):
signed Updater `PackageMigration` manifest with exact artifact identities,
no global vendor change, no repository priority change. Unlike the portal,
`gnome-shell` runs the user session, so the transition must be applied
offline and qualified with a live desktop; never replace it under a running
session.

Before closing SHELL-01: runtime regression of
audio, volume OSD, quick settings output/input selection and USB hotplug on
the patched build, the migration and its rollback, then the exact candidate
ISO checksum. Report the defect upstream to libgnome-volume-control and
prefer an official fixed SUSE package when one is available.
