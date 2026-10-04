"""Run independent scoped readers after fixture cleanup."""
from common import *
readers=('restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py')
rows={}
for name in readers:
 source=hashlib.sha256((BASE/name).read_bytes()).hexdigest()
 child=subprocess.run(['python3',str(BASE/name)],capture_output=True,text=True,timeout=60)
 rows[name]=dict(rc=child.returncode,stdout=child.stdout,stderr=child.stderr,source_sha256=source)
 assert hashlib.sha256((BASE/name).read_bytes()).hexdigest()==source
 assert child.returncode==0 and not child.stderr,(name,rows[name])
 assert json.loads(child.stdout)['passed'],name
result=dict(passed=True,readers=rows,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
(BASE/'restoration-executions.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=True,readers=list(rows))))
