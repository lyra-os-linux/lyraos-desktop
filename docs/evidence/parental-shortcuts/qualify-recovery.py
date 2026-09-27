"""Verify real enforcing-session failures and systemd's subsequent recovery."""
import json
from pathlib import Path
import sys

out = Path(__file__).resolve().parent
assert len(sys.argv) == 3, 'Expected SIGKILL and timeout evidence tags'
rows = []
for tag, fault, expected_result in zip(sys.argv[1:], ['SIGKILL', 'timeout'], ['signal', 'timeout']):
    injection = json.loads((out / f'{tag}-fault.json').read_text())
    unit = json.loads((out / f'{tag}-unit.json').read_text())
    restoration = json.loads((out / f'restoration-{tag}.json').read_text())
    assert injection['enforcing'] is True and injection['phase'] == 'preparechooser'
    assert injection['fault'] == fault
    assert f'Result={expected_result}\n' in unit['state'], unit
    assert 'ActiveState=failed\n' in unit['state'], unit
    assert restoration['restored'] is True and restoration['pending'] is False
    assert restoration['files'] == 106, restoration
    assert not (out / f'stderr-{tag}.log').read_text().strip()
    rows.append(dict(tag=tag, injection=injection, unit=unit, restoration=restoration, passed=True))
summary = dict(passed=True, cases=rows, production_enabled=False)
(out / 'recovery-tests.json').write_text(json.dumps(summary, indent=2) + '\n')
print(json.dumps(summary, indent=2))
