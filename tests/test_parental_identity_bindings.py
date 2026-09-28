"""Validate untrusted roster rejection before generating experimental PAM text."""
import copy
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'docs/evidence/parental-identity/bindings.py'
spec = importlib.util.spec_from_file_location('parental_identity_bindings', SOURCE)
bindings = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bindings)


class ParentalIdentityBindingsTests(unittest.TestCase):
    def setUp(self):
        self.roster = [dict(user='child_one', uid=27101, gid=38101, group='child_one'),
                       dict(user='child_two', uid=27102, gid=38102, group='child_two')]

    def test_two_accounts_share_one_positive_ordinary_selector(self):
        self.assertEqual(bindings.render(self.roster),
            'session [success=1 default=ignore] pam_succeed_if.so quiet '
            'user != child_one uid ne 27101 gid ne 38101 '
            'user != child_two uid ne 27102 gid ne 38102\n'
            'session required pam_lyra_identity_fixture.so '
            'account=child_one:27101:38101:child_one '
            'account=child_two:27102:38102:child_two\n')

    def test_rejects_empty_oversized_and_non_list_rosters(self):
        for value in ([], None, {}, tuple(self.roster), self.roster * 17):
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                bindings.render(value)

    def test_rejects_missing_and_extra_fields(self):
        for field in ('user', 'uid', 'gid', 'group', 'unexpected'):
            roster = copy.deepcopy(self.roster)
            if field == 'unexpected':
                roster[0][field] = 'debug'
            else:
                del roster[0][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                bindings.render(roster)
        with self.assertRaises(ValueError):
            bindings.render(['account=child:1:2:group'])

    def test_rejects_pam_injection_and_unsupported_names(self):
        for field in ('user', 'group'):
            for name in ('', 'alice\nsession optional pam_permit.so', 'a b', 'a:b',
                         'a\tdebug', '-alice', '1alice', 'Alice', 'a.b', 'é', 'a'*64, None):
                roster = copy.deepcopy(self.roster)
                roster[0][field] = name
                with self.subTest(field=field, name=name), self.assertRaises(ValueError):
                    bindings.render(roster)

    def test_rejects_invalid_reserved_and_implicitly_converted_ids(self):
        for field in ('uid', 'gid'):
            for value in (0, -1, 2**32 - 1, 2**32, True, 1.0, '123', None):
                roster = copy.deepcopy(self.roster)
                roster[0][field] = value
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    bindings.render(roster)

    def test_rejects_identity_collision_and_shared_private_groups(self):
        for field in ('user', 'uid', 'gid', 'group'):
            roster = copy.deepcopy(self.roster)
            roster[1][field] = roster[0][field]
            with self.subTest(field=field), self.assertRaises(ValueError):
                bindings.render(roster)


if __name__ == '__main__':
    unittest.main()
