import importlib.util
import pathlib
import unittest
from unittest import mock


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "bottles-pilot-evidence.py"
SPEC = importlib.util.spec_from_file_location("bottles_pilot_evidence", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


def result(command, returncode=0):
    return {"command": list(command), "returncode": returncode, "stdout": "", "stderr": ""}


class BottlesPilotEvidenceTests(unittest.TestCase):
    def test_installed_phase_requires_app(self):
        def fake_run(command):
            if command[:2] == ["flatpak", "info"] and "--show-permissions" not in command:
                return result(command)
            return result(command)

        with mock.patch.object(MODULE, "run", side_effect=fake_run):
            document = MODULE.collect("installed")

        self.assertEqual(document["status"], "observed")
        self.assertTrue(document["installed"])

    def test_before_phase_fails_when_app_is_installed(self):
        with mock.patch.object(MODULE, "run", side_effect=lambda command: result(command)):
            document = MODULE.collect("before")

        self.assertEqual(document["status"], "failed")
        self.assertFalse(document["checks"]["installation_state_matches_phase"])

    def test_removed_phase_accepts_absent_app(self):
        def fake_run(command):
            if command[:2] == ["flatpak", "info"] and "--show-permissions" not in command:
                return result(command, returncode=1)
            return result(command)

        with mock.patch.object(MODULE, "run", side_effect=fake_run):
            document = MODULE.collect("removed")

        self.assertEqual(document["status"], "observed")
        self.assertFalse(document["installed"])

    def test_review_requires_human_approval_when_removal_is_clean(self):
        before = self.snapshot("before", False)
        installed = self.snapshot("installed", True)
        installed["observations"]["flatpak_permissions"]["stdout"] = "devices=all\n"
        removed = self.snapshot("removed", False)

        document = MODULE.review(before, installed, removed)

        self.assertEqual(document["status"], "review-required")
        self.assertEqual(document["risk_markers"], ["devices=all"])
        self.assertEqual(document["automatic_blockers"], [])

    def test_review_fails_closed_on_residual_service(self):
        before = self.snapshot("before", False)
        installed = self.snapshot("installed", True)
        removed = self.snapshot("removed", False)
        removed["observations"]["user_services"]["stdout"] = "bottles-helper.service\n"

        document = MODULE.review(before, installed, removed)

        self.assertEqual(document["status"], "failed")
        self.assertIn("no_new_user_services_after_removal", document["automatic_blockers"])

    @staticmethod
    def snapshot(phase, installed):
        empty = {"returncode": 0, "stdout": "", "stderr": "", "command": []}
        return {
            "schema_version": 1,
            "kind": "bottles-pilot-snapshot",
            "phase": phase,
            "status": "observed",
            "installed": installed,
            "observations": {
                "flatpak_permissions": dict(empty),
                "flatpak_overrides": dict(empty),
                "user_services": dict(empty),
                "listening_sockets": dict(empty),
            },
        }


if __name__ == "__main__":
    unittest.main()
