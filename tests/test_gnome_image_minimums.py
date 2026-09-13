import importlib.util
from pathlib import Path
import unittest
import tempfile
import json
import xml.etree.ElementTree as ET
from unittest.mock import call, patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('minimums', ROOT / 'kiwi/root/usr/libexec/lyra/check-gnome-image.py')
minimums = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(minimums)


class MinimumsTests(unittest.TestCase):
    def image_packages(self):
        root = ET.parse(ROOT / 'kiwi/config.xml').getroot()
        return {node.attrib['name'] for group in root.findall('packages')
                if group.attrib.get('type') == 'image' and 'profiles' not in group.attrib
                for node in group.findall('package')}

    def test_required_minimums_are_explicit_in_the_gnome_image(self):
        # onlyRequired must not rely on optional frontends or incidental RPM deps.
        self.assertEqual(set(minimums.MINIMUMS) - self.image_packages(), set())

    def test_gnome_image_passes_without_the_optional_terminal_frontend(self):
        included = self.image_packages() | {'gnome-shell'}  # GNOME pattern dependency
        def installed(package):
            if package not in included:
                raise minimums.subprocess.CalledProcessError(1, ['rpm', '-q', package])
            return '48.8' if package == 'gnome-shell' else minimums.MINIMUMS[package]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for uuid in minimums.SUITE_UUIDS:
                extension = root / uuid
                extension.mkdir()
                (extension / 'metadata.json').write_text(json.dumps({
                    'uuid': uuid, 'lyra-suite-api': 1, 'shell-version': ['48']}))
            with patch.object(minimums, 'installed_version', side_effect=installed) as query, \
                    patch.object(minimums, 'Path', return_value=root):
                minimums.main()
            self.assertNotIn(call('vega-cli'), query.call_args_list)

    def test_real_rpm_comparison_rejects_stale_and_prerelease_versions(self):
        self.assertTrue(minimums.version_at_least('5.1.34', '5.1.34'))
        self.assertTrue(minimums.version_at_least('5.1.100', '5.1.34'))
        self.assertFalse(minimums.version_at_least('5.1.33', '5.1.34'))
        self.assertFalse(minimums.version_at_least('5.1.34~rc1', '5.1.34'))

    def test_no_macro_or_lua_interpolation_from_versions(self):
        with patch.object(minimums.subprocess, 'check_output') as command:
            for version in ['%{lua:print(1)}', '\"); print(1)', '1\n2', '']:
                with self.assertRaises(ValueError):
                    minimums.version_at_least(version, '1')
            command.assert_not_called()

    def test_rejects_base_extension_without_shell_48_support(self):
        base = {'uuid': 'desktop-icons@lyraos.com.br', 'lyra-suite-api': 1, 'shell-version': ['45', '46', '47']}
        with self.assertRaises(ValueError):
            minimums.check_extension('48.5', base, base['uuid'])
        minimums.check_extension('48.5', dict(base, **{'shell-version': ['48']}), base['uuid'])
        with self.assertRaises(ValueError):
            minimums.check_extension('50.0', base, base['uuid'])

    def test_missing_package_and_stale_version_fail_closed(self):
        with patch.object(minimums, 'installed_version', return_value='5.1.33'):
            with self.assertRaisesRegex(ValueError, 'vega-gtk'):
                minimums.main()
        with patch.object(minimums, 'installed_version', side_effect=minimums.subprocess.CalledProcessError(1, 'rpm')):
            with self.assertRaises(minimums.subprocess.CalledProcessError):
                minimums.main()
