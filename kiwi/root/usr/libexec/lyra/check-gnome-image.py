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
    'vega-gtk': '5.1.37', 'sheliak': '2.0.1', 'lyra-welcome': '0.4.1',
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


SUITE_UUIDS = tuple(role + '@lyraos.com.br' for role in
    ('dock', 'panel', 'menus', 'search', 'animations', 'desktop-icons'))


def check_extension(shell_version, metadata, uuid):
    major = shell_version.split('.')[0]
    if metadata.get('uuid') != uuid or major not in metadata.get('shell-version', []) or metadata.get('lyra-suite-api') != 1:
        raise ValueError(f'{uuid}: missing suite API or GNOME Shell {major} support')


def main():
    for package, minimum in MINIMUMS.items():
        actual = installed_version(package)
        if not version_at_least(actual, minimum):
            raise ValueError(f'{package}: need >= {minimum}, found {actual}')
    shell_version = installed_version('gnome-shell')
    for uuid in SUITE_UUIDS:
        metadata = json.loads((Path('/usr/share/gnome-shell/extensions') / uuid / 'metadata.json').read_text())
        check_extension(shell_version, metadata, uuid)
    print('GNOME package minimums and all six Lyra extensions passed')


if __name__ == '__main__':
    main()
