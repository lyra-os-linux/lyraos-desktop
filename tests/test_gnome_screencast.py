from __future__ import annotations

import configparser
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
OVERLAY = ROOT / "kiwi/root"
LAUNCHER = OVERLAY / "usr/libexec/lyra-gnome-screencast/org.gnome.Shell.Screencast"
COMPAT = LAUNCHER.with_name("gstreamerCompat.js")
RESOURCE = Path("/usr/share/gnome-shell/org.gnome.Shell.Screencast.src.gresource")


class GnomeScreencastTests(unittest.TestCase):
    def test_service_override_resolves_to_the_image_launcher(self) -> None:
        service = configparser.ConfigParser()
        service.read(OVERLAY / "usr/local/share/dbus-1/services/org.gnome.Shell.Screencast.service")
        definition = service["D-BUS Service"]
        self.assertEqual(definition["Name"], LAUNCHER.name)
        executable, flag, script = shlex.split(definition["Exec"])
        self.assertEqual((executable, flag), ("/usr/bin/gjs", "-m"))
        self.assertEqual(OVERLAY / script.lstrip("/"), LAUNCHER)
        self.assertTrue(LAUNCHER.is_file())
        self.assertTrue(COMPAT.is_file())
        self.assertFalse((OVERLAY / "usr/share/gnome-shell" / LAUNCHER.name).exists())

    @unittest.skipUnless(shutil.which("gjs"), "GJS is not installed")
    def test_compatibility_preserves_arguments_results_and_errors(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / "compat.mjs"
            script.write_text(f"import {{installGStreamerCompatibility}} from '{COMPAT.as_uri()}';\n" + r"""
const failure = new Error('native initialization failed');
const Gst = {
    init: argv => { if (argv === failure) throw failure; return argv; },
    init_check: argv => argv,
};
installGStreamerCompatibility(Gst);
for (const method of ['init', 'init_check']) {
    if (!Array.isArray(Gst[method](null)) || Gst[method](null).length !== 0)
        throw new Error('null arguments were not normalized');
    const argv = ['recorder', '--gst-debug=2'];
    if (Gst[method](argv) !== argv)
        throw new Error('explicit arguments or native result changed');
}
try { Gst.init(failure); throw new Error('native error was swallowed'); }
catch (error) { if (error !== failure) throw error; }
""", encoding="utf-8")
            subprocess.run(["gjs", "-m", str(script)], check=True, capture_output=True, text=True)

    @unittest.skipUnless(shutil.which("gjs") and RESOURCE.exists(),
                         "GNOME screencast runtime is not installed")
    def test_native_recorder_initializes_through_the_production_launcher(self) -> None:
        # Replace only the service main loop: exercise the packaged launcher,
        # GStreamer and native capability check without opening a display or
        # recording the developer's session.
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "main.js").write_text("""
import Gst from 'gi://Gst?version=1.0';
import {ScreencastService} from './screencastService.js';
export async function main() {
    Gst.init(null);
    const [ok] = Gst.init_check(null);
    if (!ok || !ScreencastService.canScreencast())
        throw new Error('Native screen recording is unavailable');
    print('native recorder supported');
}
""", encoding="utf-8")
            environment = dict(os.environ)
            environment["G_RESOURCE_OVERLAYS"] = f"/org/gnome/Shell/Screencast/js={directory}"
            environment["GST_REGISTRY"] = str(Path(directory) / "registry.bin")
            result = subprocess.run(["gjs", "-m", str(LAUNCHER)], check=True,
                                    capture_output=True, text=True, env=environment)
            self.assertIn("native recorder supported", result.stdout)


if __name__ == "__main__":
    unittest.main()
