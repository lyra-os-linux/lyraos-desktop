from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/prepare-controlled-successor.py"
SPEC = importlib.util.spec_from_file_location("controlled_successor", SCRIPT)
assert SPEC and SPEC.loader
controlled = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = controlled
SPEC.loader.exec_module(controlled)


class ControlledSuccessorTests(unittest.TestCase):
    def arguments(self, output: Path):
        return type("Arguments", (), {
            "output_dir": output,
            "manifest_tool": ROOT.parent / "lyraos-desktop-updater/scripts/release-manifest.py",
            "repository_url": "https://download.example.test/lyra-successor/",
            "repository_key_url": "https://download.example.test/lyra-successor/repodata/repomd.xml.key",
            "repository_key_fingerprint": "A" * 40,
            "sequence": 1,
            "valid_from": "2026-08-31T00:00:00Z",
            "valid_until": "2026-09-30T00:00:00Z",
            "signing_key": None,
        })()

    def test_prepares_atomic_successor_and_canonical_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "successor"
            controlled.prepare(self.arguments(output))
            product = (output / "rpm/lyra-product-release").read_text(encoding="utf-8")
            spec = (output / "rpm/lyra-release.spec").read_text(encoding="utf-8")
            manifest = json.loads((output / "manifest/releases-v1.json").read_text(encoding="utf-8"))
            self.assertIn("Version:        1.1~beta.1", spec)
            self.assertIn("LYRA_VERSION_ID='1.1-beta.1'", product)
            self.assertIn("LYRA_BUILD_ID='lyra-release-1.1-beta.1'", product)
            self.assertEqual(manifest["source"]["build_id"], "lyra-release-1.0")
            self.assertEqual(manifest["target"]["build_id"], "lyra-release-1.1-beta.1")
            self.assertEqual(manifest["status"], "testing")

    def test_refuses_existing_output_and_untrusted_repository_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "successor"
            output.mkdir()
            with self.assertRaisesRegex(controlled.PreparationError, "must not already exist"):
                controlled.prepare(self.arguments(output))
            output.rmdir()
            arguments = self.arguments(output)
            arguments.repository_url = "http://download.example.test/repo"
            with self.assertRaisesRegex(controlled.PreparationError, "HTTPS"):
                controlled.prepare(arguments)


if __name__ == "__main__":
    unittest.main()
