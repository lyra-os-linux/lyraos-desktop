"""VM-only native CLI account denial, composed with the vendor PAM stack.

No policy installation or account enrollment. Supervised command-line/SSH
entry points are denied entirely; application execution remains a separate MAC
contract. Reuses the explicit local-identity validation from the earlier stage.
"""
import importlib.util
from pathlib import Path

_source = Path(__file__).resolve().parents[1] / 'parental-identity/bindings.py'
_spec = importlib.util.spec_from_file_location('identity_bindings', _source)
_bindings = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bindings)


def render(accounts):
    selector = _bindings.render(accounts).splitlines()[0]
    return selector.replace('session ', 'account ', 1) + '\naccount requisite pam_deny.so\n'


def compose(vendor, accounts):
    if not isinstance(vendor, str) or not vendor.startswith('#%PAM-1.0\n'):
        raise ValueError('unrecognized vendor PAM header')
    lines = [line.split() for line in vendor.splitlines() if line.strip() and not line.startswith('#')]
    if not any(line[0] == 'account' for line in lines):
        raise ValueError('vendor PAM account stack is missing')
    # Prepend rather than append: a successful vendor control must never skip
    # the supervised denial. Preserve every original authentication/session line.
    return '#%PAM-1.0\n# Experimental supervised CLI denial\n' + render(accounts) + vendor[len('#%PAM-1.0\n'):]
