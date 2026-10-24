import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "scripts/i18n-result.py"
SPEC = importlib.util.spec_from_file_location("lyra_i18n_result", TOOL)
assert SPEC and SPEC.loader
i18n_result = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = i18n_result
SPEC.loader.exec_module(i18n_result)

LOCALES = ["en-US", "pt-BR", "es-ES"]


def write_candidate(directory: Path, packages: dict[str, str]) -> Path:
    iso = directory / "LyraOS-Desktop-1.1-alpha.8-x86_64.iso"
    iso.write_bytes(b"candidate")
    (directory / f"{iso.name}.manifest.json").write_text(
        json.dumps(
            {
                "iso": {"filename": iso.name, "sha256": hashlib.sha256(b"candidate").hexdigest()},
                "source": {"commit": "a" * 40},
            }
        ),
        encoding="utf-8",
    )
    rows = [f"{name}|(none)|{version}|lp161.1.1|noarch|obs://example/{name}|GPL-3.0-only" for name, version in packages.items()]
    (directory / "LyraOS-Desktop-1.1-alpha.8-x86_64.packages").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return iso


def write_inventory(path: Path, entries: list[dict]) -> Path:
    path.write_text(
        json.dumps({"schema": 1, "locales": LOCALES, "default_locale": "en-US", "fallback_locale": "en-US", "packages": entries}),
        encoding="utf-8",
    )
    return path


def entry(package: str, status: str) -> dict:
    return {"id": package, "project": "lyra", "status": status, "format": "gettext", "rationale": f"{package} rationale"}


def review(path: Path, package: str, version: str, status: str = "passed") -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": 1,
                "status": status,
                "mode": "i18n-package-review",
                "package": package,
                "version": version,
                "reviewed_at": "2026-10-10T17:34:18+00:00",
                "locales": LOCALES,
                "fallback": "en-US",
                "checks": [{"id": "message-en-US", "status": status}],
            }
        ),
        encoding="utf-8",
    )
    return path


class I18nResultTests(unittest.TestCase):
    def test_generates_one_check_per_shipped_inventory_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root, {"beam": "1.0.1", "zed": "1.16.1", "lyra-vms": "0.1.0"})
            inventory = write_inventory(
                root / "inventory.json",
                [entry("beam", "complete"), entry("zed", "not-applicable"), entry("lyra-vms", "complete"), entry("legacy-frontend", "scheduled")],
            )
            reviews = {"lyra-vms": review(root / "lyra-vms-review.json", "lyra-vms", "0.1.0-lp161.1.1")}
            result, iso = i18n_result.generate(root, inventory, reviews)
            self.assertEqual(result["status"], "passed")
            self.assertEqual(result["mode"], "i18n")
            self.assertEqual(result["locales"], LOCALES)
            self.assertEqual(result["candidate"]["iso"], iso.name)
            self.assertEqual(result["candidate"]["commit"], "a" * 40)
            by_id = {check["id"]: check for check in result["checks"]}
            self.assertEqual(set(by_id), {"i18n-beam", "i18n-zed", "i18n-lyra-vms"})
            self.assertEqual(by_id["i18n-beam"]["scope"], "complete")
            self.assertEqual(by_id["i18n-beam"]["version"], "1.0.1-lp161.1.1")
            self.assertEqual(by_id["i18n-zed"]["scope"], "not-applicable")
            self.assertEqual(by_id["i18n-lyra-vms"]["scope"], "candidate-review")
            self.assertEqual(by_id["i18n-lyra-vms"]["catalog_evidence"], "lyra-vms-review.json")
            self.assertEqual([item["id"] for item in result["excluded_not_in_candidate"]], ["legacy-frontend"])
            self.assertEqual(result["excluded_not_in_candidate"][0]["status"], "scheduled")

    def test_scheduled_package_that_ships_fails_the_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root, {"legacy-frontend": "5.1.0"})
            inventory = write_inventory(root / "inventory.json", [entry("legacy-frontend", "scheduled")])
            result, _ = i18n_result.generate(root, inventory, {})
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["checks"][0]["status"], "failed")

    def test_package_review_must_match_the_shipped_version_and_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root, {"lyra-vms": "0.1.0"})
            inventory = write_inventory(root / "inventory.json", [entry("lyra-vms", "complete")])
            stale = {"lyra-vms": review(root / "stale.json", "lyra-vms", "0.1.0-lp161.9.9")}
            result, _ = i18n_result.generate(root, inventory, stale)
            self.assertEqual(result["status"], "failed")
            self.assertIn("ISO ships", result["checks"][0]["detail"])
            failed = {"lyra-vms": review(root / "failed.json", "lyra-vms", "0.1.0-lp161.1.1", status="failed")}
            result, _ = i18n_result.generate(root, inventory, failed)
            self.assertEqual(result["status"], "failed")
            with self.assertRaisesRegex(i18n_result.GenerationError, "absent from the candidate"):
                write_candidate(root, {"beam": "1.0.1"})
                i18n_result.generate(root, write_inventory(root / "inventory.json", [entry("beam", "complete"), entry("lyra-vms", "complete")]), failed)

    def test_cli_refuses_to_write_a_failed_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root, {"legacy-frontend": "5.1.0"})
            inventory = write_inventory(root / "inventory.json", [entry("legacy-frontend", "scheduled")])
            output = root / "i18n-result.json"
            completed = subprocess.run(
                [sys.executable, str(TOOL), "--iso-dir", str(root), "--inventory", str(inventory), "--output", str(output)],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("i18n gate failed for: i18n-legacy-frontend", completed.stderr)
            self.assertFalse(output.exists())

    def test_cli_writes_a_result_the_release_contract_accepts(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_candidate(root, {"beam": "1.0.1"})
            inventory = write_inventory(root / "inventory.json", [entry("beam", "complete")])
            output = root / "i18n-result.json"
            subprocess.run(
                [sys.executable, str(TOOL), "--iso-dir", str(root), "--inventory", str(inventory), "--output", str(output)],
                check=True,
                capture_output=True,
            )
            document = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(document["status"], "passed")
            self.assertEqual(document["generated_by"], "scripts/i18n-result.py")
            self.assertEqual(document["fallback"], "en-US")


if __name__ == "__main__":
    unittest.main()
