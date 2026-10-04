"""Actual typed systemd properties and fingerprints; never starts or stops units."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,os,stat,subprocess
from reference import SPECS,capture,check,LocalIdentity,configuration
from namespace import Namespace
from coordinator import GateError
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/systemd-reference-test');BASE.mkdir(mode=0o700,exist_ok=True)
previous=json.loads(Path('/root/service-catalog-test/result.json').read_text());assert previous['passed']
reader=Namespace(['/usr/lib/systemd/system'],str(BASE/'unused.lock'))
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,(args,p.stderr);return p.stdout

def file_data(path,limit=32*1024*1024):
 fd=reader.open_absolute(path)
 try:
  s=os.fstat(fd);assert s.st_size<=limit;data=[];left=s.st_size+1
  while left:
   chunk=os.read(fd,min(left,65536))
   if not chunk:break
   data.append(chunk);left-=len(chunk)
  data=b''.join(data);assert len(data)==s.st_size and reader.stamp(os.fstat(fd))==reader.stamp(s)
  return data,reader.stamp(s)
 finally:os.close(fd)
def fingerprint(path):
 data,stamp=file_data(path);return stamp+(hashlib.sha256(data).hexdigest(),)
def user(name):
 data,_=file_data('/etc/passwd',65536);rows=[s.split(':') for s in data.decode().splitlines() if s.split(':',1)[0]==name];assert len(rows)==1
 return LocalIdentity(name,int(rows[0][2]),int(rows[0][3]))
def group(name):
 data,_=file_data('/etc/group',65536);rows=[s.split(':') for s in data.decode().splitlines() if s.split(':',1)[0]==name];assert len(rows)==1;return int(rows[0][2])
def properties(unit):
 output=json.loads(run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','LoadUnit','s',unit]));assert output['type']=='o' and len(output['data'])==1
 path=output['data'][0];assert path.startswith('/org/freedesktop/systemd1/unit/')
 result={}
 for name in SPECS:
  interface='org.freedesktop.systemd1.'+('Unit' if name in ('Id','Names','LoadState','FragmentPath','DropInPaths','NeedDaemonReload') else 'Service')
  result[name]=json.loads(run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',path,interface,name]))
 return result
checks=[]
def record(name,**fields):checks.append(dict(name=name,passed=True,**fields));print(json.dumps(checks[-1]),flush=True)
def expect(code,fn):
 try:fn()
 except GateError as e:assert e.code==code,(e.code,code)
 else:raise AssertionError('missing '+code)
meta=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),broker_pid=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip(),source_sha256={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('native.py','reference.py','namespace.py','catalog.py','coordinator.py')})
original_accounts={p:fingerprint(p) for p in ('/etc/passwd','/etc/group','/etc/pam.d/systemd-user')}
refs=[];unsupported=[];passed=False;error=None
try:
 for row in previous['original_declarations']:
  if not row['systemd_unit']:continue
  try:r=capture(row['systemd_unit'],properties,user,group,fingerprint)
  except GateError as e:unsupported.append(dict(name=row['name'],code=e.code));continue
  refs.append((row['name'],r));record('typed-unit-reference-'+row['name'],reference=asdict(r),declared_user=row['declared_identity']['user'])
 assert refs
 for name,r in refs:assert check(r,properties,user,group,fingerprint)==r
 record('all-captured-references-revalidated',captured=len(refs),unsupported=unsupported)
 polkit=next(r for name,r in refs if name=='org.freedesktop.PolicyKit1')
 assert polkit.configuration.identity.user=='polkitd' and polkit.configuration.argv!=tuple(next(row['argv'] for row in previous['original_declarations'] if row['name']=='org.freedesktop.PolicyKit1'))
 record('configured-unit-user-and-argv-distinguished-from-dbus-declaration',identity=asdict(polkit.configuration.identity),argv=polkit.configuration.argv)
 # Fault injection uses typed observations/fingerprint adapters. No vendor file is edited.
 raw=properties('polkit.service');raw['NeedDaemonReload']['data']=True
 expect('UnverifiedLoadedUnit',lambda:configuration('polkit.service',raw,user,group))
 record('stale-loaded-configuration-refused-without-reload-or-effects')
 def altered(path):
  value=fingerprint(path)
  return value+('fault',) if path==polkit.configuration.fragment else value
 expect('Conflict',lambda:check(polkit,properties,user,group,altered))
 record('changed-source-observation-refuses-existing-reference')
 assert original_accounts=={p:fingerprint(p) for p in original_accounts}
 assert run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()==meta['broker_pid']
 record('account-pam-files-and-shared-broker-preserved',broker_pid=meta['broker_pid'])
 passed=True
except BaseException as e:error=str(e);raise
finally:
 row=dict(passed=passed,error=error,checks=checks,metadata=meta,references=[dict(name=name,**asdict(r)) for name,r in refs],unsupported=unsupported,original_accounts=original_accounts,full_account_protection=False,global_coverage_qualified=False,running_credentials_qualified=False,real_activation_or_revocation_tested=False,storage_fault_injection_real=False)
 (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(dict(passed=passed,checks=len(checks))))
