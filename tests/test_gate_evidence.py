import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "kiwi/test/gate-evidence.py"
LIVE = ROOT / "kiwi/test/guest/live-gate.sh"
INSTALLED = ROOT / "kiwi/test/guest/installed-gate.sh"
SPEC = importlib.util.spec_from_file_location("lyra_gate_evidence", TOOL)
assert SPEC and SPEC.loader
gate_evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = gate_evidence
SPEC.loader.exec_module(gate_evidence)


def report(mode: str, status: str = "passed") -> dict:
    return {"schema": 1, "status": status, "mode": mode, "checks": [{"id": f"{mode}-check", "status": status}]}


def block(tool: str, section: str, body: str, exit_code: int = 0) -> str:
    return f"### BEGIN {tool} {section} 2026-10-13T12:00:00Z user=liveuser kernel=6.12.0\n{body}\n### END {tool} {section} exit={exit_code}\n"


def stream_text() -> str:
    return (
        '{"schema":1,"status":"observed","mode":"guest-upgrade-state"}\n'
        + block("live-gate", "live-session", json.dumps(report("live-session", "failed")), 1)
        + block("live-gate", "live-session", json.dumps(report("live-session"), indent=2))
        + block("live-gate", "firmware", "## mokutil\nSecureBoot enabled")
        + block("live-gate", "installer", "## home\n-rw lyra-installer-result.json\n## installer-result\n" + json.dumps(report("installer"), indent=2) + "\n## lsblk\nvda 24G")
        + block("installed-gate", "first-boot", json.dumps(report("first-boot"), indent=2))
        + block("installed-gate", "uefi-secure-boot", json.dumps(report("uefi-secure-boot"), indent=2))
    )


class GateEvidenceTests(unittest.TestCase):
    def test_extracts_the_last_passed_report_of_each_json_section(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stream = Path(temporary) / "stream.jsonl"
            stream.write_text(stream_text(), encoding="utf-8")
            for section in ("live-session", "installer", "first-boot", "uefi-secure-boot"):
                block_, report_ = gate_evidence.extract(stream, section)
                self.assertEqual(block_["exit"], 0)
                self.assertEqual(report_["mode"], gate_evidence.JSON_SECTIONS[section])
                self.assertEqual(report_["status"], "passed")
            block_, report_ = gate_evidence.extract(stream, "firmware")
            self.assertIsNone(report_)
            self.assertIn("SecureBoot enabled", block_["body"])

    def test_rejects_failed_or_missing_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stream = Path(temporary) / "stream.jsonl"
            stream.write_text(block("live-gate", "live-session", json.dumps(report("live-session", "failed")), 1), encoding="utf-8")
            with self.assertRaisesRegex(gate_evidence.EvidenceError, "exited with 1"):
                gate_evidence.extract(stream, "live-session")
            stream.write_text(block("live-gate", "live-session", json.dumps(report("live-session", "failed")), 0), encoding="utf-8")
            with self.assertRaisesRegex(gate_evidence.EvidenceError, "not passed"):
                gate_evidence.extract(stream, "live-session")
            stream.write_text(block("live-gate", "live-session", json.dumps(report("installer")), 0), encoding="utf-8")
            with self.assertRaisesRegex(gate_evidence.EvidenceError, "mode is 'installer'"):
                gate_evidence.extract(stream, "live-session")
            with self.assertRaisesRegex(gate_evidence.EvidenceError, "not found"):
                gate_evidence.extract(stream, "first-boot")

    def test_cli_writes_results_accepted_by_the_release_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stream = root / "stream.jsonl"
            stream.write_text(stream_text(), encoding="utf-8")
            (root / "candidate.iso").write_bytes(b"iso")
            for section in ("live-session", "installer", "first-boot", "uefi-secure-boot"):
                output = root / f"{section}-result.json"
                transcript = root / f"{section}-guest-output.txt"
                subprocess.run(
                    [sys.executable, str(TOOL), "--guest-evidence", str(stream), "--section", section, "--output", str(output), "--transcript", str(transcript), "--iso-dir", str(root)],
                    check=True,
                    capture_output=True,
                )
                self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["status"], "passed")
                self.assertTrue(transcript.read_text(encoding="utf-8").startswith("### BEGIN"))
            completed = subprocess.run(
                [sys.executable, str(TOOL), "--guest-evidence", str(stream), "--section", "firmware", "--output", str(root / "x.json")],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)

    def test_guest_scripts_stream_every_gate_section_through_the_evidence_port(self) -> None:
        for script_path, tool, sections in (
            (LIVE, "live-gate", ("live-session", "live-session-offline", "firmware", "repositories", "identity", "journal-crit", "installer")),
            (INSTALLED, "installed-gate", ("first-boot", "uefi-secure-boot", "journal-crit", "packages", "palette", "locale", "users", "sudo-policy")),
        ):
            subprocess.run(["bash", "-n", str(script_path)], check=True)
            script = script_path.read_text(encoding="utf-8")
            self.assertTrue(script_path.stat().st_mode & 0o111)
            self.assertIn("/dev/virtio-ports/org.lyraos.UpgradeEvidence", script)
            self.assertIn(f'echo "### BEGIN {tool} $section $stamp', script)
            self.assertIn(f'echo "### END {tool} $section exit=$status"', script)
            for section in sections:
                self.assertIn(f"    {section}) stream {section} ", script)
        self.assertIn("lyra-live-smoke", LIVE.read_text(encoding="utf-8"))
        self.assertIn("--expect-offline", LIVE.read_text(encoding="utf-8"))
        self.assertIn("lyra-system-smoke", INSTALLED.read_text(encoding="utf-8"))
        self.assertIn("sudo -v || exit 1", INSTALLED.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
