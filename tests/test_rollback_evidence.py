import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "kiwi/test/rollback-evidence.py"
GUEST = ROOT / "kiwi/test/guest/rollback-gate.sh"
SPEC = importlib.util.spec_from_file_location("lyra_rollback_evidence", TOOL)
assert SPEC and SPEC.loader
rollback_evidence = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = rollback_evidence
SPEC.loader.exec_module(rollback_evidence)

PHASES = ("baseline", "update", "verify-updated", "prepare-rollback", "verify-rollback")


def report(phase: str, status: str, workflow_phase: str) -> dict:
    return {
        "schema": 1,
        "status": status,
        "mode": "rollback",
        "phase": workflow_phase,
        "generated_at": "2026-10-15T10:00:00+00:00",
        "checks": [{"id": f"{phase}-check", "status": "passed" if status != "failed" else "failed", "detail": phase}],
        "facts": {"kernel": "6.12.0-fixture"},
    }


def block(phase: str, document: dict, exit_code: int = 0) -> str:
    return (
        f"### BEGIN rollback-gate {phase} 2026-10-15T10:00:00Z host=lyra kernel=6.12.0-fixture\n"
        + json.dumps(document, indent=2)
        + f"\n### END rollback-gate {phase} exit={exit_code}\n"
    )


def full_run(final_status: str = "passed", final_phase: str = "rollback-verified") -> str:
    workflow = {
        "baseline": "baseline",
        "update": "updated",
        "verify-updated": "updated-verified",
        "prepare-rollback": "rollback-prepared",
    }
    text = '{"schema":1,"status":"observed","mode":"guest-upgrade-state"}\n'
    for phase in PHASES[:-1]:
        text += block(phase, report(phase, "incomplete", workflow[phase]))
    text += block("verify-rollback", report("verify-rollback", final_status, final_phase), 0 if final_status == "passed" else 1)
    return text


class RollbackEvidenceTests(unittest.TestCase):
    def test_assembles_the_final_verified_report_from_the_guest_stream(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stream = Path(temporary) / "upgrade-guest-evidence.jsonl"
            # An earlier aborted exercise followed by the complete one.
            stream.write_text(block("baseline", report("baseline", "incomplete", "baseline")) + full_run(), encoding="utf-8")
            result, run = rollback_evidence.assemble(stream)
            self.assertEqual(result["phase"], "rollback-verified")
            self.assertEqual(result["status"], "passed")
            self.assertEqual([item["phase"] for item in run], list(PHASES))

    def test_rejects_incomplete_or_failed_exercises(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            stream = Path(temporary) / "stream.jsonl"
            stream.write_text(full_run()[: full_run().index("### BEGIN rollback-gate verify-rollback")], encoding="utf-8")
            with self.assertRaisesRegex(rollback_evidence.EvidenceError, "verify-rollback is missing"):
                rollback_evidence.assemble(stream)
            stream.write_text(full_run(final_status="failed", final_phase="rollback-prepared"), encoding="utf-8")
            with self.assertRaisesRegex(rollback_evidence.EvidenceError, "exited with 1"):
                rollback_evidence.assemble(stream)
            stream.write_text(full_run(final_phase="rollback-prepared"), encoding="utf-8")
            with self.assertRaisesRegex(rollback_evidence.EvidenceError, "not rollback-verified"):
                rollback_evidence.assemble(stream)
            text = full_run().replace(block("update", report("update", "incomplete", "updated")), block("update", report("update", "failed", "update-failed"), 1))
            stream.write_text(text, encoding="utf-8")
            with self.assertRaisesRegex(rollback_evidence.EvidenceError, "phase update failed"):
                rollback_evidence.assemble(stream)

    def test_cli_writes_result_and_transcript_accepted_by_the_release_policy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stream = root / "stream.jsonl"
            stream.write_text(full_run(), encoding="utf-8")
            (root / "candidate.iso").write_bytes(b"iso")
            output, transcript = root / "rollback-result.json", root / "rollback-transcript.json"
            subprocess.run(
                [sys.executable, str(TOOL), "--guest-evidence", str(stream), "--output", str(output), "--transcript", str(transcript), "--iso-dir", str(root)],
                check=True,
                capture_output=True,
            )
            self.assertEqual(json.loads(output.read_text(encoding="utf-8"))["phase"], "rollback-verified")
            self.assertEqual(len(json.loads(transcript.read_text(encoding="utf-8"))), 5)

    def test_guest_script_streams_every_phase_through_the_evidence_port(self) -> None:
        script = GUEST.read_text(encoding="utf-8")
        subprocess.run(["bash", "-n", str(GUEST)], check=True)
        self.assertTrue(GUEST.stat().st_mode & 0o111)
        self.assertIn("/dev/virtio-ports/org.lyraos.UpgradeEvidence", script)
        self.assertIn("baseline|update|verify-updated|prepare-rollback|verify-rollback", script)
        self.assertIn('lyra-update-smoke "$PHASE" --output "$REPORT"', script)
        self.assertIn('echo "### BEGIN rollback-gate $PHASE $STAMP', script)
        self.assertIn('echo "### END rollback-gate $PHASE exit=$STATUS"', script)
        # A failed phase never reboots the VM into the next step.
        self.assertIn('[ "$REBOOT" -eq 1 ] && [ "$STATUS" -eq 0 ]', script)


if __name__ == "__main__":
    unittest.main()
