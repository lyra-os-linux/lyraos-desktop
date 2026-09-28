import importlib.util
from pathlib import Path
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'docs/evidence/parental-transitions/transition.py'
spec = importlib.util.spec_from_file_location('parental_transition', SOURCE)
transition = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transition)


class ProcessIdentityTests(unittest.TestCase):
    def test_all_four_process_uids_prevent_an_idle_claim(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            for n, row in enumerate(('21000 0 0 0', '0 21000 0 0', '0 0 21000 0', '0 0 0 21000', '0 0 0 0'), 1):
                (proc / str(n)).mkdir()
                (proc / str(n) / 'status').write_text('Name:\tsleep\nUid:\t' + row + '\n')
            self.assertEqual(transition.processes(21000, proc), [1, 2, 3, 4])

    def test_missing_or_malformed_identity_cannot_mean_idle(self):
        for text in ('', 'Uid: 1000', 'Uid: 1000 1000 x 1000', 'Uid: -1 0 0 0',
                     'Uid: 0 0 0 0\nUid: 0 0 0 0', 'Uid: ٠ 0 0 0'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                transition.process_owners(text)

    def test_disappeared_process_is_allowed_but_corrupt_status_aborts(self):
        with tempfile.TemporaryDirectory() as directory:
            proc = Path(directory)
            (proc / '123').mkdir()
            self.assertEqual(transition.processes(21000, proc), [])
            (proc / '123' / 'status').write_text('Uid: broken')
            with self.assertRaises(ValueError):
                transition.processes(21000, proc)

    def test_record_rejects_injection_and_reserved_ids(self):
        normal = dict(user='child', uid=21000, gid=23000, group='child')
        for field, value in [('user', 'child\nactive=root'), ('group', 'a:b'), ('uid', 0),
                             ('uid', True), ('gid', 2**32 - 1), ('uid', '21000')]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                transition.active_record(dict(normal, **{field: value}))


if __name__ == '__main__':
    unittest.main()
