"""Fail-closed solver gate for the two qualified portal artifacts, VM experiment only.

Vendor identities come from signature/hash-checked RPMs and installed RPM queries;
zypper's repository alias is never used as a vendor identity.
"""
import xml.etree.ElementTree as ET

NAME = 'xdg-desktop-portal-gnome'
ARCHES = {NAME: 'x86_64', NAME + '-lang': 'noarch'}
SUSE = ('48.0-160100.2.1', 'SUSE LLC <https://www.suse.com/>')
STAGING = ('48.0-160100.2.1.lyra1.160101.1',
           'obs://build.opensuse.org/home:rodrigosbrito')


class PlanError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise PlanError(message)


def validate_plan(xml, before, after):
    """Validate exact package sets, editions, architectures and directed transitions.

    before/after map package names to [edition, vendor]. Language presence must
    remain unchanged. Payloads are supplied as verified local RPMs, not selected
    by a mutable repository URL. This gate does not execute any command.
    """
    require(set(before) == set(after) and NAME in before and set(before) <= set(ARCHES),
            'unexpected package set or changed language presence')
    for state in [before, after]:
        require(all(tuple(value) in [SUSE, STAGING] for value in state.values()),
                'unqualified edition/vendor')
        require(len({tuple(value) for value in state.values()}) == 1,
                'main/language versions must move together')
    require(len(xml) < 2_000_000 and '<!DOCTYPE' not in xml and '<!ENTITY' not in xml,
            'unexpected XML size or declaration')
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise PlanError('invalid solver XML') from error
    require(root.tag == 'stream', 'unexpected XML root')
    require(not root.findall('.//message[@type="error"]') and not root.findall('.//problem'),
            'solver error')
    summaries = root.findall('.//install-summary')
    require(len(summaries) == 1, 'missing or duplicate summary')
    summary = summaries[0]
    changed = {name for name in before if tuple(before[name]) != tuple(after[name])}
    require(summary.get('packages-to-change') == str(len(changed)), 'change count mismatch')
    observed, vendors = set(), set()
    for group in summary:
        require(group.tag in ['to-upgrade', 'to-downgrade', 'to-change-vendor'],
                'unexpected action: ' + group.tag)
        require(len(group) > 0, 'empty action group')
        for item in group:
            name = item.get('name')
            require(item.tag == 'solvable' and item.get('type') == 'package' and name in changed,
                    'unexpected package')
            fields = dict(arch=ARCHES[name], edition=after[name][0],
                          repository='_tmpRPMcache_', **{'arch-old': ARCHES[name],
                                                       'edition-old': before[name][0]})
            require(all(item.get(k) == value for k, value in fields.items()),
                    'package identity mismatch')
            action = 'to-upgrade' if tuple(after[name]) == STAGING else 'to-downgrade'
            require(group.tag in [action, 'to-change-vendor'], 'wrong transition direction')
            seen = vendors if group.tag == 'to-change-vendor' else observed
            require(name not in seen, 'duplicate package action')
            seen.add(name)
    require(observed == changed and vendors == changed, 'missing package/vendor action')
    return sorted(changed)
