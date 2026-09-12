import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('minimums', ROOT / 'kiwi/root/usr/libexec/lyra/check-gnome-image.py')
minimums = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(minimums)


class MinimumsTests(unittest.TestCase):
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
        base = {'uuid': 'ding@rastersoft.com', 'shell-version': ['45', '46', '47']}
        with self.assertRaises(ValueError):
            minimums.check_desktop_icons('48.5', base)
        minimums.check_desktop_icons('48.5', dict(base, **{'shell-version': ['46', '47', '48', '49']}))
        with self.assertRaises(ValueError):
            minimums.check_desktop_icons('50.0', base)

    def test_missing_package_and_stale_version_fail_closed(self):
        with patch.object(minimums, 'installed_version', return_value='5.1.33'):
            with self.assertRaisesRegex(ValueError, 'vega-gtk'):
                minimums.main()
        with patch.object(minimums, 'installed_version', side_effect=minimums.subprocess.CalledProcessError(1, 'rpm')):
            with self.assertRaises(minimums.subprocess.CalledProcessError):
                minimums.main()
