# Desktop branding packages

The GNOME image explicitly installs `lyra-nautilus-branding` and
`libreoffice-branding-Lyra`. The image uses onlyRequired, so recommending the
Nautilus package from the theme alone does not select it for a new installation.
The LibreOffice package supplies the existing `libreoffice-branding` capability
and replaces the openSUSE provider in the image's normal RPM transaction.

Both source packages belong to the shared Lyra OBS inventory maintained by the
GNOME release manifest. The new default selection is limited to GNOME. KDE/XFCE
integration and publication are paused by the maintainer's
[GNOME focus decision](gnome-focus.md).

The maintainer approved both designs locally and authorized release integration.
The Nautilus module was tested with the actual RPM in 50 isolated native cases;
LibreOffice startup and PDF export passed with its extracted RPM in a private
session. The host installed both RPMs successfully. Release promotion additionally
requires successful OBS builds, signed RPM verification, payload comparison and
the existing staging gates. These checks do not qualify a complete installer ISO.

Rollback: remove the Nautilus branding package, then start a new Nautilus process.
For LibreOffice, replace the Lyra branding provider with
`libreoffice-branding-openSUSE` in one package-manager transaction. Neither
package edits user profiles. Revert the two explicit image package entries to
restore the previous default selection in future images. Keep the OBS inventory
in sync with actual projects until packages are explicitly retired.
