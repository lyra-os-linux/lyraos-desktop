"""liveuser's locked password must not block polkit admin actions in the live session."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / 'kiwi/config.sh').read_text()
RULE_PATH = '/etc/polkit-1/rules.d/49-lyra-liveuser.rules'


def live_rule():
    match = re.search(r"cat > %s <<'EOF'\n(.*?)\nEOF\n" % re.escape(RULE_PATH), CONFIG, re.S)
    if not match:
        raise AssertionError('liveuser polkit rule not found in kiwi/config.sh')
    return match.group(1)


class LivePolkitTests(unittest.TestCase):
    def test_rule_is_scoped_to_liveuser_local_active_session(self):
        rule = live_rule()
        self.assertIn('subject.user == "liveuser" && subject.local && subject.active', rule)
        self.assertIn('return polkit.Result.YES;', rule)

    def test_rule_runs_before_vendor_defaults(self):
        self.assertLess(Path(RULE_PATH).name, '50-default.rules')

    def test_installer_removes_rule(self):
        deploy = (ROOT / 'installer/src/service/operations/deploy.rs').read_text()
        artifacts = deploy.split('const LIVE_ONLY_ARTIFACTS', 1)[1].split('];', 1)[0]
        self.assertIn('"%s"' % RULE_PATH.lstrip('/'), artifacts)
        self.assertIn('"etc/sudoers.d/00-liveuser-nopasswd"', artifacts)

    def test_live_gate_checks_authorization(self):
        gate = (ROOT / 'kiwi/test/guest/live-gate.sh').read_text()
        self.assertIn('pkcheck --action-id org.lyraos.vega.software.install', gate)
        self.assertRegex(gate, r'all\) SECTIONS\+=\([^)]*\bpolkit\b')

    @unittest.skipUnless(shutil.which('node'), 'node not installed')
    def test_rule_is_valid_javascript(self):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp, 'rule.js')
            script.write_text(
                'const calls = [];\n'
                'const polkit = { Result: { YES: "yes" }, addRule: (f) => calls.push(f) };\n'
                + live_rule() + '\n'
                'const rule = calls[0];\n'
                'const yes = rule({}, { user: "liveuser", local: true, active: true });\n'
                'const other = rule({}, { user: "rodrigo", local: true, active: true });\n'
                'const remote = rule({}, { user: "liveuser", local: false, active: true });\n'
                'if (yes !== "yes" || other !== undefined || remote !== undefined) process.exit(1);\n')
            subprocess.run(['node', str(script)], check=True)


if __name__ == '__main__':
    unittest.main()
