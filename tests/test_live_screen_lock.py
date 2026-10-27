"""The live session must never lock a screen that liveuser cannot unlock."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = (ROOT / 'kiwi/config.sh').read_text()


def live_keyfile():
    match = re.search(r"cat > \"\$lyra_live_dconf/00-lyra-live-session\" <<'EOF'\n(.*?)\nEOF\n", CONFIG, re.S)
    if not match:
        raise AssertionError('live dconf keyfile not found in kiwi/config.sh')
    return match.group(1)


class LiveScreenLockTests(unittest.TestCase):
    def test_liveuser_password_is_locked(self):
        image = ET.parse(ROOT / 'kiwi/config.xml').getroot()
        self.assertEqual(image.find("users/user[@name='liveuser']").attrib['password'], '!')

    def test_live_session_disables_lock_and_idle_blanking(self):
        keyfile = live_keyfile()
        self.assertIn('[org/gnome/desktop/screensaver]\nlock-enabled=false', keyfile)
        self.assertIn('[org/gnome/desktop/session]\nidle-delay=uint32 0', keyfile)

    def test_setting_is_scoped_to_liveuser_home(self):
        self.assertIn('dconf compile /home/liveuser/.config/dconf/user "$lyra_live_dconf"', CONFIG)
        self.assertNotIn('/etc/dconf/db', CONFIG)
        deploy = (ROOT / 'installer/src/service/operations/deploy.rs').read_text()
        self.assertIn('--remove liveuser', deploy)

    @unittest.skipUnless(shutil.which('dconf'), 'dconf not installed')
    def test_keyfile_compiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp, 'keyfiles')
            source.mkdir()
            (source / '00-lyra-live-session').write_text(live_keyfile() + '\n')
            subprocess.run(['dconf', 'compile', str(Path(tmp, 'user')), str(source)], check=True)
            self.assertGreater(Path(tmp, 'user').stat().st_size, 0)


if __name__ == '__main__':
    unittest.main()
