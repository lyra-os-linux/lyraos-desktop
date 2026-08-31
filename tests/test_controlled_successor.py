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
        repositories = output.parent / "repositories.json"
        aliases = sorted(controlled.REQUIRED_REPOSITORIES)
        repositories.write_text(json.dumps([
            {
                "alias": alias,
                "base_url": f"https://download.example.test/{alias}/",
                "signing_key_url": f"https://download.example.test/{alias}/key.asc",
                "signing_key_fingerprint": "A" * 40,
                "priority": index + 1,
            }
            for index, alias in enumerate(aliases)
        ]), encoding="utf-8")
        return type("Arguments", (), {
            "output_dir": output,
            "manifest_tool": ROOT.parent / "lyraos-desktop-updater/scripts/release-manifest.py",
            "repositories": repositories,
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
            document = json.loads(arguments.repositories.read_text(encoding="utf-8"))
            document.pop()
            arguments.repositories.write_text(json.dumps(document), encoding="utf-8")
            with self.assertRaisesRegex(controlled.PreparationError, "exact controlled target"):
                controlled.prepare(arguments)


if __name__ == "__main__":
    unittest.main()
