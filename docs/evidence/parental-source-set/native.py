"""Actual installed sources + BrokerFence; callbacks are read-only test markers."""
from pathlib import Path
import fcntl,hashlib,json,os,shlex,subprocess
from sources import SourceSet
from binding import BrokerFence
from coordinator import GateError
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/source-set-test');BASE.mkdir(mode=0o700,exist_ok=True)
prior=json.loads(Path('/root/dbus-config-audit/result.json').read_text());assert prior['passed']
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,(args,p.stderr);return p.stdout

def names():
 parts=shlex.split(run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListActivatableNames']));assert parts[0]=='as' and int(parts[1])==len(parts)-2;return set(parts[2:])
def reload():run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ReloadConfig'])
lock=BASE/'sources.lock';assert not lock.exists();lock.write_bytes(b'');lock.chmod(0o600)
override=Path('/etc/dbus-1/system-local.conf');assert not override.exists() and not override.is_symlink()
roots=['/usr/share/dbus-1/system.d','/etc/dbus-1/system.d','/usr/share/dbus-1/system-services','/usr/local/share/dbus-1/system-services','/usr/lib/dbus-1/system-services']
assert os.readlink('/lib')=='usr/lib'
files=sorted(set(prior['files'])|{str(override)})
namespace=SourceSet(roots,files,[str(override)],str(lock),aliases=(('/lib','usr/lib'),))
initial=namespace.plan();known={e.path:e.digest for e in initial.entries if e.digest}
def classified():
 return {e.path:e.digest for e in namespace.snapshot().entries if e.digest}==known
fence=BrokerFence(namespace,classified,names,[])
checks=[];effects=[];created_files=[];created_dirs=[];passed=False;error=None
before=names();broker=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()
meta=dict(broker_pid=broker,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),packages=run(['rpm','-q','dbus-broker','dbus-1']),source_sha256={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('native.py','sources.py','namespace.py','binding.py','coordinator.py')})
config_before={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in prior['files']}
assert config_before=={p:row['sha256'] for p,row in prior['files'].items()}
assert meta['packages']==prior['metadata']['packages']
accounts={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group','/etc/pam.d/systemd-user')}
def record(name,**fields):checks.append(dict(name=name,passed=True,**fields));print(json.dumps(checks[-1]),flush=True)
def expect(code,fn):
 try:fn()
 except GateError as e:assert e.code==code,(e.code,code)
 else:raise AssertionError('missing '+code)
def effect():effects.append('readonly-marker');return True
def repair():
 for p in reversed(created_files):p.unlink()
 created_files.clear()
 for p in reversed(created_dirs):p.rmdir()
 created_dirs.clear();reload()
def create(path,text):
 assert not path.exists() and not path.is_symlink()
 missing=[];parent=path.parent
 while not parent.exists():missing.append(parent);parent=parent.parent
 for p in reversed(missing):p.mkdir(mode=0o755);created_dirs.append(p)
 path.write_text(text);path.chmod(0o644);created_files.append(path)
try:
 record('real-graph-files-roots-absences-and-alias-bound',roots=roots,files=len(files),missing=[x[0] for x in initial.missing],alias='/lib -> usr/lib')
 plan=fence.plan();expect('Denied',lambda:fence.execute(plan,lambda _:False,[effect]));assert not effects
 record('denial-preserves-sources-and-prevents-marker')
 def optional_after_auth(_):
  with lock.open('rb') as f:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB);create(override,'<busconfig/>\n')
  return True
 expect('Conflict',lambda:fence.execute(plan,optional_after_auth,[effect]));assert not effects
 expect('UnsupportedProducer',fence.plan)
 record('optional-override-creation-refuses-old-and-unclassified-new-plan',effects=effects.copy());repair()
 for index,root in enumerate(roots[-2:]):
  plan=fence.plan();path=Path(root)/('org.lyra.SourceSet.Alternative'+str(index)+'.service')
  def authorize(_,p=path,i=index):create(p,'[D-BUS Service]\nName=org.lyra.SourceSet.Alternative'+str(i)+'\nUser=root\nExec=/usr/bin/false\n');return True
  expect('Conflict',lambda:fence.execute(plan,authorize,[effect]));assert not effects
  expect('UnsupportedProducer',fence.plan)
  record('alternative-root-creation-refuses-before-marker-'+str(index),root=root,effects=effects.copy());repair()
 plan=fence.plan();policy=Path(roots[0])/'lyra-source-set-test.conf'
 def first():effects.append('first-readonly-marker');create(policy,'<busconfig/>\n') # Root fault outside cooperative writer lock.
 expect('Conflict',lambda:fence.execute(plan,lambda _:True,[first,effect]));assert effects==['first-readonly-marker']
 record('vendor-policy-added-between-callbacks-prevents-second-marker',effects=effects.copy());repair()
 plan=fence.plan()
 def guarded():
  with lock.open('rb') as f:
   try:fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
   except BlockingIOError:pass
   else:raise AssertionError('writer acquired EX')
  return True
 assert fence.execute(plan,lambda _:True,[guarded])==(True,)
 record('fresh-reconciled-source-plan-and-writer-exclusion')
 assert config_before=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in config_before}
 assert accounts=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in accounts}
 assert names()==before and run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()==broker
 record('original-configuration-accounts-pam-loaded-set-and-broker-preserved',broker_pid=broker)
 passed=True
except BaseException as e:error=str(e);raise
finally:
 repair();lock.unlink()
 row=dict(passed=passed,error=error,checks=checks,metadata=meta,configuration_hashes=config_before,account_hashes=accounts,created_paths_removed=not created_files and not created_dirs,full_account_protection=False,global_coverage_qualified=False,graph_semantics_qualified=False,real_revocation_tested=False)
 (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(dict(passed=passed,checks=len(checks))))
