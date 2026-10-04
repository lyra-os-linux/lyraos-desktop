"""Marked VM declarations and ambiguity controls; no activation or revocation."""
from pathlib import Path
from dataclasses import asdict
import hashlib,json,os,shlex,subprocess
from sources import SourceSet
from catalog import catalog,LocalIdentity,require_adapters
from coordinator import GateError
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/service-catalog-test');BASE.mkdir(mode=0o700,exist_ok=True)
prior=json.loads(Path('/root/dbus-config-audit/result.json').read_text());assert prior['passed']
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,(args,p.stderr);return p.stdout

def names():
 parts=shlex.split(run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListActivatableNames']));assert parts[0]=='as' and int(parts[1])==len(parts)-2;return set(parts[2:])
lock=BASE/'sources.lock';assert not lock.exists();lock.write_bytes(b'');lock.chmod(0o600)
roots=['/usr/local/share/dbus-1/system-services','/usr/share/dbus-1/system-services','/usr/lib/dbus-1/system-services']
ns=SourceSet(roots+['/usr/share/dbus-1/system.d','/etc/dbus-1/system.d'],list(prior['files'])+['/etc/dbus-1/system-local.conf'],['/etc/dbus-1/system-local.conf'],str(lock),aliases=(('/lib','usr/lib'),))
def file_bytes(path):
 fd=ns.open_absolute(path)
 try:
  s=os.fstat(fd);assert s.st_size<=65536;data=os.read(fd,65537);assert len(data)==s.st_size and ns.stamp(os.fstat(fd))==ns.stamp(s);return data
 finally:os.close(fd)
passwd=file_bytes('/etc/passwd');group=file_bytes('/etc/group')
def resolve(user):
 rows=[r.split(':') for r in passwd.decode().splitlines() if r.split(':',1)[0]==user]
 if len(rows)!=1:raise GateError('InvalidIdentity')
 uid,gid=map(int,rows[0][2:4]);groups=[r for r in group.decode().splitlines() if r.split(':')[2]==str(gid)]
 if len(groups)!=1:raise GateError('InvalidIdentity')
 return LocalIdentity(user,uid,gid)
def declarations(snapshot):
 rows=[]
 for entry in snapshot.entries:
  path=Path(entry.path)
  if str(path.parent) in roots and path.suffix=='.service':
   data=file_bytes(str(path));assert hashlib.sha256(data).hexdigest()==entry.digest;rows.append((str(path),data))
 result=catalog(rows,resolve);ns.check(snapshot)
 assert file_bytes('/etc/passwd')==passwd and file_bytes('/etc/group')==group
 return result
checks=[]
def record(name,**fields):checks.append(dict(name=name,passed=True,**fields));print(json.dumps(checks[-1]),flush=True)
def expect(code,fn):
 try:fn()
 except GateError as e:assert e.code==code,(e.code,code)
 else:raise AssertionError('missing '+code)
original=ns.plan();rows=declarations(original);assert len(rows)==13
before=names();broker=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()
meta=dict(broker_pid=broker,boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),source_sha256={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('native.py','catalog.py','sources.py','namespace.py','coordinator.py')})
created=[];dirs=[];passed=False;error=None
fixture_name='org.lyra.CatalogProbe.Known'
def create(root,data):
 path=Path(root)/(fixture_name+'.service');assert not path.exists() and not path.is_symlink();missing=[];parent=path.parent
 while not parent.exists():missing.append(parent);parent=parent.parent
 for p in reversed(missing):p.mkdir(mode=0o755);dirs.append(p)
 path.write_bytes(data);path.chmod(0o644);created.append(path)
def repair():
 for p in reversed(created):p.unlink()
 created.clear()
 for p in reversed(dirs):p.rmdir()
 dirs.clear()
try:
 record('installed-13-declarations-typed-with-local-passwd-and-group',declarations=[asdict(r) for r in rows])
 observations=[]
 for row in rows:
  if not row.systemd_unit:continue
  text=run(['systemctl','show',row.systemd_unit,'-p','Id','-p','LoadState','-p','User','-p','Group','-p','PAMName','-p','DynamicUser','-p','FragmentPath','-p','DropInPaths'])
  fields=dict(line.split('=',1) for line in text.splitlines());effective=fields.get('User') or 'root'
  observations.append(dict(name=row.name,declared_user=row.declared_identity.user,unit=row.systemd_unit,observed=fields,user_differs=effective!=row.declared_identity.user))
 record('declared-users-and-actual-systemd-fields-kept-separate',observations=observations)
 expect('UnsupportedProducer',lambda:require_adapters(rows,{}))
 record('root-and-system-declarations-do-not-bypass-required-adapters')
 data=('[D-BUS Service]\nName='+fixture_name+'\nUser=ordinaryuser\nExec=/usr/bin/false\n').encode()
 create(roots[1],data);snapshot=ns.plan();current=declarations(snapshot);fixture=next(r for r in current if r.name==fixture_name)
 assert fixture.declared_identity.uid==1002
 expect('UnsupportedProducer',lambda:require_adapters(current,{}))
 record('target-local-uid-declared-without-granting-producer-coverage',identity=asdict(fixture.declared_identity))
 create(roots[0],data);expect('AmbiguousProducerCatalog',lambda:declarations(ns.plan()))
 record('identical-name-and-content-across-real-roots-refused')
 # Different execution definitions are equally ambiguous; no precedence winner is chosen.
 created[-1].write_bytes(data.replace(b'/usr/bin/false',b'/usr/bin/true'))
 expect('AmbiguousProducerCatalog',lambda:declarations(ns.plan()))
 record('conflicting-execution-definition-across-real-roots-refused');repair()
 create(roots[1],data+b'FutureActivation=yes\n');expect('UnsupportedServiceDefinition',lambda:declarations(ns.plan()))
 record('unknown-activation-field-refused');repair()
 assert declarations(ns.plan())==rows and file_bytes('/etc/passwd')==passwd and file_bytes('/etc/group')==group
 run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ReloadConfig'])
 assert names()==before and run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()==broker
 record('original-catalog-account-files-loaded-set-and-broker-preserved',broker_pid=broker)
 passed=True
except BaseException as e:error=str(e);raise
finally:
 repair();lock.unlink()
 result=dict(passed=passed,error=error,checks=checks,metadata=meta,original_declarations=[asdict(r) for r in rows],account_hashes={'/etc/passwd':hashlib.sha256(passwd).hexdigest(),'/etc/group':hashlib.sha256(group).hexdigest()},full_account_protection=False,global_coverage_qualified=False,systemd_execution_binding_qualified=False,precedence_resolution_qualified=False,real_activation_or_revocation_tested=False)
 (BASE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(passed=passed,checks=len(checks))))
