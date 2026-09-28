"""Render a VM-only PAM fragment from explicit local-account bindings.

Pure generation only: this does not enroll accounts or install PAM policy.
The selector and module arguments must be deployed as one root-owned file.
"""
import re

NAME = re.compile(r'[a-z_][a-z0-9_-]{0,62}\Z')
FIELDS = {'user', 'uid', 'gid', 'group'}
def render(accounts):
    if not isinstance(accounts, list) or not 1 <= len(accounts) <= 32:
        raise ValueError('expected 1..32 account bindings')
    used = {field: set() for field in FIELDS}
    selectors, arguments = [], []
    for item in accounts:
        if not isinstance(item, dict) or set(item) != FIELDS:
            raise ValueError('unexpected binding fields')
        for field in ('user', 'group'):
            if not isinstance(item[field], str) or not NAME.fullmatch(item[field]):
                raise ValueError('invalid account/group name')
        for field in ('uid', 'gid'):
            if type(item[field]) is not int or not 0 < item[field] < 2**32 - 1:
                raise ValueError('invalid UID/GID')
        for field in FIELDS:
            if item[field] in used[field]:
                raise ValueError('ambiguous or shared binding')
            used[field].add(item[field])
        selectors.append(f"user != {item['user']} uid ne {item['uid']} gid ne {item['gid']}")
        arguments.append(f"account={item['user']}:{item['uid']}:{item['gid']}:{item['group']}")
    return ('session [success=1 default=ignore] pam_succeed_if.so quiet ' + ' '.join(selectors) + '\n'
            'session required pam_lyra_identity_fixture.so ' + ' '.join(arguments) + '\n')
