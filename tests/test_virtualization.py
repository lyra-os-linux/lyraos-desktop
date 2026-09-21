"""Contracts for a usable, local-only virtualization stack in the image."""
from pathlib import Path
import subprocess
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


class VirtualizationTests(unittest.TestCase):
    def test_required_only_image_includes_backend_and_default_network(self):
        image = ET.parse(ROOT / 'kiwi/config.xml').getroot()
        packages = {p.attrib['name'] for group in image.findall('packages')
                    if group.attrib.get('type') == 'image' and 'profiles' not in group.attrib
                    for p in group.findall('package')}
        required = {'virt-manager', 'virt-install', 'libvirt-daemon-qemu',
                    'libvirt-daemon-config-network', 'libvirt-client', 'qemu',
                    'qemu-x86', 'qemu-img', 'qemu-ovmf-x86_64', 'qemu-ui-gtk',
                    'qemu-ui-opengl', 'qemu-hw-display-virtio-vga'}
        self.assertFalse(required - packages, required - packages)

    def test_live_access_does_not_change_installed_account_policy(self):
        image = ET.parse(ROOT / 'kiwi/config.xml').getroot()
        live = image.find("users/user[@name='liveuser']")
        self.assertIn('libvirt', live.attrib['groups'].split(','))
        self.assertEqual(live.attrib['password'], '!')
        deploy = (ROOT / 'installer/src/service/operations/deploy.rs').read_text()
        groups = deploy.split('const USER_SUPPLEMENTARY_GROUPS:', 1)[1].split('];', 1)[0]
        self.assertNotIn('"libvirt"', groups)
        self.assertIn('"wheel"', groups)
        rules = ROOT / 'kiwi/root/etc/polkit-1/rules.d'
        self.assertFalse(any('org.libvirt.unix.manage' in p.read_text() for p in rules.glob('*.rules')),
                         'Do not replace vendor authentication with a global allow rule')

    def test_image_configures_sockets_without_starting_network_or_guests(self):
        helper = ROOT / 'kiwi/root/usr/libexec/lyra/configure-virtualization'
        subprocess.run(['bash', '-n', str(helper)], check=True)
        self.assertTrue(helper.stat().st_mode & 0o111)
        text = helper.read_text()
        for socket in ('virtqemud', 'virtnetworkd', 'virtstoraged', 'virtsecretd',
                       'virtnodedevd', 'virtlogd', 'virtlockd'):
            self.assertIn(socket + '.socket', text)
        for forbidden in ('--now', 'systemctl start', '-tcp.socket', '-tls.socket',
                          'virsh net-start', 'virsh net-autostart', 'virt-install '):
            self.assertNotIn(forbidden, text)
        self.assertIn('/usr/libexec/lyra/configure-virtualization',
                      (ROOT / 'kiwi/config.sh').read_text())
