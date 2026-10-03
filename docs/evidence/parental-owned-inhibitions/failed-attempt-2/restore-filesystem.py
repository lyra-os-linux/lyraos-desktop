from common import *
row=dict(passed=not (BASE/'filesystem-scratch').exists(),scratch_absent=not (BASE/'filesystem-scratch').exists())
(BASE/'filesystem-restored-independent.json').write_text(json.dumps(row)+'\n');print(json.dumps(row));assert row['passed']
