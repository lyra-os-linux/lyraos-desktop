#!/usr/bin/python3
"""Reject stale GNOME packages before finalizing the next Lyra image.

This checks minimum versions and Shell compatibility, not release provenance.
Signed RPMs and accepted OBS source revisions remain separate release gates.
"""
import json
from pathlib import Path
import re
import subprocess

MINIMUMS = {
    'vega-gtk': '5.1.34', 'sheliak': '1.16.0', 'lyra-welcome': '0.4.0',
    'gnome-shell-extension-desktop-icons': '49.0.5',
    'lyra-os-theme': '1.9.3', 'lyra-os-icons': '1.9.4',
    'lyra-nautilus-branding': '1.9.3', 'libreoffice-branding-Lyra': '1.0.0',
    'linuxtoys': '6.9', 'lyra-upgrade': '0.2.3', 'beam': '1.0.1',
    'sulafat': '1.0.4', 'vega-cli': '5.1.22', 'vegad': '5.1.26',
    'lyra-installer': '0.1.0',
}


def installed_version(package):
    return subprocess.check_output(
        ['rpm', '-q', '--qf', '%{VERSION}', package], text=True).strip()


def version_at_least(actual, minimum):
    # Accept RPM version punctuation but prohibit Lua/macro interpolation.
    if not all(re.fullmatch(r'[A-Za-z0-9._+~^:-]+', v) for v in (actual, minimum)):
        raise ValueError('invalid RPM version')
    result = subprocess.check_output([
        'rpm', '--eval', '%{lua:print(rpm.vercmp("' + actual + '", "' + minimum + '"))}'
    ], text=True).strip()
    return int(result) >= 0


def check_desktop_icons(shell_version, metadata):
    major = shell_version.split('.')[0]
    if metadata.get('uuid') != 'ding@rastersoft.com' or major not in metadata.get('shell-version', []):
        raise ValueError(f'Desktop Icons NG does not support GNOME Shell {major}')


def main():
    for package, minimum in MINIMUMS.items():
        actual = installed_version(package)
        if not version_at_least(actual, minimum):
            raise ValueError(f'{package}: need >= {minimum}, found {actual}')
    metadata = json.loads(Path('/usr/share/gnome-shell/extensions/ding@rastersoft.com/metadata.json').read_text())
    check_desktop_icons(installed_version('gnome-shell'), metadata)
    print('GNOME package minimums and Desktop Icons NG compatibility passed')


if __name__ == '__main__':
    main()
