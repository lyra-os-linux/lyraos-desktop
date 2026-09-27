import copy
import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / 'docs/evidence/portal-transition'
spec = importlib.util.spec_from_file_location('portal_policy', EVIDENCE / 'policy.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)


class PortalTransitionPolicyTests(unittest.TestCase):
    def setUp(self):
        self.xml = (EVIDENCE / 'plan.xml').read_text()
        self.before = {policy.NAME: list(policy.SUSE)}
        self.after = {policy.NAME: list(policy.STAGING)}

    def check(self, xml=None, before=None, after=None):
        return policy.validate_plan(xml or self.xml, before or self.before, after or self.after)

    def test_native_single_package_plan(self):
        self.assertEqual(self.check(), [policy.NAME])

    def test_unrelated_removal_and_extra_package_are_rejected(self):
        for tag, name in [('to-remove', 'gnome-shell'), ('to-upgrade', 'glibc')]:
            root = ET.fromstring(self.xml)
            summary = root.find('install-summary')
            item = copy.deepcopy(summary.find('to-upgrade/solvable'))
            item.set('name', name)
            ET.SubElement(summary, tag).append(item)
            summary.set('packages-to-change', '2')
            with self.subTest(tag=tag), self.assertRaises(policy.PlanError):
                self.check(ET.tostring(root, encoding='unicode'))

    def test_identity_changes_and_unknown_vendor_are_rejected(self):
        for key, value in [('arch', 'i586'), ('arch-old', 'noarch'),
                           ('edition', '99.0-1'), ('edition-old', '48.0-999'),
                           ('repository', 'untrusted')]:
            root = ET.fromstring(self.xml)
            root.find('.//solvable').set(key, value)
            with self.subTest(key=key), self.assertRaises(policy.PlanError):
                self.check(ET.tostring(root, encoding='unicode'))
        for state in [self.before, self.after]:
            changed = copy.deepcopy(state)
            changed[policy.NAME][1] = 'different vendor'
            with self.assertRaises(policy.PlanError):
                self.check(before=changed if state is self.before else None,
                           after=changed if state is self.after else None)

    def test_missing_duplicate_unknown_actions_and_errors_are_rejected(self):
        for mutation in ['missing', 'duplicate', 'unknown', 'error', 'count', 'direction']:
            root = ET.fromstring(self.xml)
            summary = root.find('install-summary')
            if mutation == 'missing': summary.remove(summary.find('to-change-vendor'))
            if mutation == 'duplicate': summary.append(copy.deepcopy(summary[0]))
            if mutation == 'unknown': ET.SubElement(summary, 'to-change-arch')
            if mutation == 'error': ET.SubElement(root, 'message', type='error').text = 'failure'
            if mutation == 'count': summary.set('packages-to-change', '0')
            if mutation == 'direction': summary[0].tag = 'to-downgrade'
            with self.subTest(mutation=mutation), self.assertRaises(policy.PlanError):
                self.check(ET.tostring(root, encoding='unicode'))

    def test_malformed_xml_and_ambiguous_summaries_are_rejected(self):
        for xml in ['broken', '<stream/>', '<wrong/>', '<!DOCTYPE stream><stream/>',
                    '<stream><install-summary/><install-summary/></stream>']:
            with self.subTest(xml=xml), self.assertRaises(policy.PlanError): self.check(xml)

    def test_language_presence_and_version_coupling_are_preserved(self):
        after = {**self.after, policy.NAME + '-lang': list(policy.STAGING)}
        with self.assertRaises(policy.PlanError): self.check(after=after)
        before = {**self.before, policy.NAME + '-lang': list(policy.STAGING)}
        with self.assertRaises(policy.PlanError): self.check(before=before, after=after)

    def test_idempotent_plan_must_really_be_empty(self):
        xml = '<stream><install-summary packages-to-change="0"/></stream>'
        self.assertEqual(self.check(xml, before=self.after), [])
        with self.assertRaises(policy.PlanError): self.check(before=self.after)


if __name__ == '__main__': unittest.main()
