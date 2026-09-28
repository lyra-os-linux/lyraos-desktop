import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'docs/evidence/parental-entries/policy.py'
spec = importlib.util.spec_from_file_location('cli_policy', SOURCE)
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class CliPolicyTests(unittest.TestCase):
    def setUp(self):
        self.accounts = [dict(user='child', uid=31000, gid=41000, group='child'),
                         dict(user='otherchild', uid=31001, gid=41001, group='otherchild')]

    def test_only_positive_ordinary_identity_skips_account_denial(self):
        self.assertEqual(policy.render(self.accounts),
            'account [success=1 default=ignore] pam_succeed_if.so quiet '
            'user != child uid ne 31000 gid ne 41000 '
            'user != otherchild uid ne 31001 gid ne 41001\n'
            'account requisite pam_deny.so\n')

    def test_denial_precedes_vendor_short_circuit_without_losing_authentication(self):
        vendor = '#%PAM-1.0\nauth required pam_unix.so\naccount sufficient pam_permit.so\nsession required pam_unix.so\n'
        composed = policy.compose(vendor, self.accounts)
        self.assertLess(composed.index('account requisite pam_deny.so'), composed.index('account sufficient pam_permit.so'))
        self.assertTrue(composed.endswith(vendor.split('\n', 1)[1]))

    def test_empty_registry_or_injected_name_cannot_create_permissive_policy(self):
        with self.assertRaises(ValueError):
            policy.render([])
        self.accounts[0]['user'] = 'child\naccount sufficient pam_permit.so'
        with self.assertRaises(ValueError):
            policy.render(self.accounts)

    def test_unknown_vendor_stack_is_refused(self):
        for vendor in ('account required pam_unix.so\n', '#%PAM-1.0\nauth required pam_unix.so\n', None):
            with self.subTest(vendor=vendor), self.assertRaises(ValueError):
                policy.compose(vendor, self.accounts)


if __name__ == '__main__':
    unittest.main()
