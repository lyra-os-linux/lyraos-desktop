from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'kiwi/root/etc/dracut.conf.d/99-lyra-live-plymouth.conf'


class LivePlymouthTests(unittest.TestCase):
    def omitted(self, modules):
        return subprocess.check_output([
            'bash', '-c',
            'add_dracutmodules="$1"; omit_dracutmodules=" multipath "; '
            'source "$2"; printf "%s" "$omit_dracutmodules"',
            'test', modules, str(CONFIG),
        ], text=True).split()

    def test_live_context_omits_both_modules_and_preserves_prior_omissions(self):
        self.assertEqual(self.omitted(' kiwi-live pollcdrom '),
                         ['multipath', 'plymouth', 'lyra-plymouth'])

    def test_installed_system_keeps_plymouth(self):
        for modules in ('', ' crypt btrfs ', ' kiwi-live-other '):
            with self.subTest(modules=modules):
                self.assertEqual(self.omitted(modules), ['multipath'])
