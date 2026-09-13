# GNOME desktop icons, Lyra layouts and the next image

The maintainer approved one Sheliak repository and RPM containing six independent
GNOME extensions: Dock, Panel, Menus, Search, Animations and Lyra Desktop Icons
(LDI). The architecture decision and qualification requirements are recorded in
[sheliak-extension-suite-plan.md](sheliak-extension-suite-plan.md).

GNOME is the only desktop release target. The ISO is built locally with KIWI;
OBS supplies RPM sources and packages. Updating this recipe does not submit an
ISO build or qualify a live/installed login.

## Desktop icons

LDI is maintained inside `lyraos-desktop-sheliak/extensions/desktop-icons`, based
on [Desktop Icons NG](https://gitlab.com/rastersoft/desktop-icons-ng) 49.0.5,
commit `c32667693d0831c29e3ab3f7bfeb675ea1531a00`. Its auxiliary GTK/GJS application,
Nautilus integration, GPL licenses and upstream credits remain. The Portuguese
and Spanish catalogs each contain 190 translated messages; English uses source
strings. Provenance and future upstream updates are documented in `UPSTREAM.md`.

The `sheliak` RPM owns all six extension directories and the desktop helper's
runtime dependencies. It replaces the previously shipped standalone
`gnome-shell-extension-desktop-icons` RPM. The old Desktop-side DING packaging
is retired; do not publish another divergent DING recipe. Keep historical OBS
provenance records unchanged and retain the remote old package until replacement
and rollback qualification finish.

New/live GNOME users receive unlocked defaults for the six Lyra UUIDs. Existing
users migrate in their own session using `/usr/libexec/lyra/shell-suite migrate`;
the login helper allows up to 30 seconds for Shell service startup before migrating UUIDs;
the protected snapshot preserves their preferences, explicit disabled states
and unrelated extensions. The helper disables old Sheliak/DING before enabling
the replacements. It does not move or delete Desktop files. The Vega GTK Active
desktop switch remains independent of all six layouts and respects GNOME's
global extension disable setting.

## Profiles and coordinated versions

The visible names are Lyra, GNOME Vanilla, Ubuntu, Lyra Classic, Lyra Central and
Lyra Floating, localized in Portuguese, English and Spanish. The persisted IDs
`windows10`, `windows11` and `macos` remain compatible with saved favorites,
menu cards and presentation snapshots.

This image requires Vega GTK >=5.1.37, Sheliak >=2.0.1, Welcome >=0.4.1
and lyra-nautilus-branding >=1.9.4. The Nautilus module must recognize the
independent shell UUIDs; the retired monolithic UUID is no longer sufficient.
Welcome delegates profile changes to Vega. The suite helper journals changes
before Vega changes the layout and restores interrupted transactions at retry
or login. Independent component selections are remembered per layout; desktop
icons remain a separate preference, including in GNOME Vanilla.

## Image qualification

`kiwi/config.sh` runs `check-gnome-image.py` inside the prepared image. It checks
all six UUIDs, suite API version 1 and GNOME major compatibility, in addition to
minimum versions of branding, themes, LinuxToys and other GNOME components.
The separate OBS provenance/signature gates require accepted source revisions;
minimum versions alone cannot identify sources reusing a version number.

Before releasing the next ISO:

- Qualify and publish the compatible RPM set through staging/release gates.
- Record signed package inventory and accepted source revisions.
- Verify live and first installed login, six profiles, light/dark appearance,
  favorites, cards and desktop switch in Portuguese, English and Spanish.
- Verify files, folders, Trash, mounted volumes and drag-and-drop with Nautilus,
  including multiple monitors, HiDPI, suspend/resume and a fresh user.
- Retain installer, firmware, hardware, update and rollback release gates.

Native development tests use disposable HOME and GNOME sessions. Prior manual
validation of DING drag-and-drop on 12 September does not replace qualification
of this new package or the next ISO.

## Reversal

Keep the previous compatible Sheliak/Vega/Welcome/DING RPM set. Before replacing
the new RPMs with that set, run `/usr/libexec/lyra/shell-suite rollback` in the
user session; this restores owned settings from the migration snapshot while
preserving later third-party extension changes. Reinstall the compatible old
RPMs and start a new login. Do not force hot reload. Desktop files are untouched.
Revert image defaults and minimum versions together if abandoning the candidate.
