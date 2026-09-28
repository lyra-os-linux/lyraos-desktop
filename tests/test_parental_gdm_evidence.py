import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'docs/evidence/parental-managers/gdm-evidence.py'
spec = importlib.util.spec_from_file_location('gdm_evidence', SOURCE)
evidence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(evidence)


def conversation(module=evidence.MODULE):
    worker, manager = 'host gdm-autologin][21]: ', 'host gdm[10]: '
    return '\n'.join([
        worker + 'Gdm: GdmSessionWorker: initializing PAM; service=gdm-autologin username=child seat=seat0',
        worker + f'PAM unable to dlopen({module}): missing',
        worker + 'Gdm: GdmSessionWorker: attempting to change state to SESSION_OPENED',
        worker + 'pam_lyra_transition_fixture(gdm-autologin:session): Experimental supervised admission rejected session',
        worker + 'Gdm: GdmSessionWorker: state NONE',
        manager + 'Gdm: GdmSessionWorkerJob: Stopping job pid:21',
        manager + "Gdm: GdmSession: Emitting 'session-start-failed' signal",
        manager + 'Gdm: GdmSessionWorkerJob: child (pid:21) done (status:0)',
    ])


class GdmEvidenceTests(unittest.TestCase):
    def test_complete_rejection_requires_correct_cause_and_completion(self):
        for missing in (False, True):
            result = evidence.rejection(conversation(), 10, 'child', missing)
            self.assertEqual(result['worker_pid'], 21)
            self.assertEqual(len(result['lines']), 7)

    def test_optional_module_warning_cannot_prove_missing_lyra(self):
        self.assertIsNone(evidence.rejection(conversation('/usr/lib64/security/pam_gnome_keyring.so'), 10, 'child', True))

    def test_load_error_or_partial_conversation_is_insufficient(self):
        rows = conversation().splitlines()
        for length in range(1, len(rows)):
            self.assertIsNone(evidence.rejection('\n'.join(rows[:length]), 10, 'child', True))

    def test_unrelated_worker_manager_or_account_cannot_supply_completion(self):
        self.assertIsNone(evidence.rejection(conversation(), 99, 'child', True))
        self.assertIsNone(evidence.rejection(conversation(), 10, 'other', True))
        self.assertIsNone(evidence.rejection(conversation().replace('Stopping job pid:21', 'Stopping job pid:22'), 10, 'child', True))
        self.assertIsNone(evidence.rejection(conversation().replace('gdm-autologin][21]: Gdm: GdmSessionWorker: state NONE',
                                                                  'gdm-autologin][22]: Gdm: GdmSessionWorker: state NONE'), 10, 'child', True))

    def test_wrong_order_is_not_a_completed_rejection(self):
        self.assertIsNone(evidence.rejection('\n'.join(reversed(conversation().splitlines())), 10, 'child', True))

    def test_later_success_invalidates_negative_claim(self):
        for line in ("host gdm[10]: Gdm: GdmSession: Emitting 'session-started' signal with pid '30'",
                     'host gdm-autologin][21]: Gdm: GdmSessionWorker: state SESSION_STARTED'):
            self.assertIsNone(evidence.rejection(conversation() + '\n' + line, 10, 'child', True))


if __name__ == '__main__':
    unittest.main()
