"""Exercise the proposed GDM hook fix with native SELinux fault injection."""
import json
from pathlib import Path
import subprocess
import sys
import unittest


class GdmHookContextTests(unittest.TestCase):
    def test_context_is_preserved_and_errors_refuse_the_session(self):
        script = (Path(__file__).resolve().parents[1] / "docs/evidence"
                  / "parental-gdm/test-hook-context.py")
        result = subprocess.run([sys.executable, str(script)], capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cases = json.loads(result.stdout)["results"]
        self.assertEqual([case["result"] for case in cases],
                         ["8 SELinux hook cases PASS", "2 non-SELinux hook cases PASS"])


if __name__ == "__main__":
    unittest.main()
