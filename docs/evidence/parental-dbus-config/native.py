"""Marked VM config dependency audit and non-activating source-directory probes."""
from pathlib import Path
import ctypes,hashlib,json,os,shlex,stat,subprocess
from dataclasses import asdict
from dependencies import dependencies
from namespace import Namespace
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/dbus-config-audit');BASE.mkdir(mode=0o700,exist_ok=True)
PREFIX='org.lyra.ConfigAudit.'
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,(args,p.stderr);return p.stdout

def names():
 parts=shlex.split(run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListActivatableNames']));assert parts[0]=='as' and int(parts[1])==len(parts)-2;return set(parts[2:])
def reload():run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ReloadConfig'])
def pid():return run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()
checks=[]
def record(name,**fields):checks.append(dict(name=name,passed=True,**fields));print(json.dumps(checks[-1]),flush=True)
reader=Namespace(['/usr/share/dbus-1'],str(BASE/'unused.lock')) # Only secure path-opening primitive is used; never creates lock.
files={};edges=[];missing=[];directories={};unsupported=[];seen=set();stack=set()
selinux=ctypes.CDLL('libselinux.so.1');selinux.selinux_policy_root.restype=ctypes.c_char_p
policy_root=selinux.selinux_policy_root().decode();enabled=bool(selinux.is_selinux_enabled()>0)
def read(path):
 fd=reader.open_absolute(path)
 try:
  s=os.fstat(fd);assert s.st_size<=65536
  data=os.read(fd,65537);assert len(data)==s.st_size and reader.stamp(os.fstat(fd))==reader.stamp(s)
  files[path]=dict(sha256=hashlib.sha256(data).hexdigest(),stamp=reader.stamp(s));return data
 finally:os.close(fd)
def visit(path):
 if path in stack:raise RuntimeError('include cycle')
 if path in seen:return
 if len(seen)>=128:raise RuntimeError('config graph limit')
 stack.add(path);seen.add(path)
 for d in dependencies(read(path),path):
  edge=dict(source=path,**asdict(d));edges.append(edge)
  if d.kind=='standard_system_servicedirs':continue # Version-specific factory below, not guessed by parser.
  target=d.path
  if d.kind=='selinux-include':
   if d.condition and not enabled:edge['skipped_condition']=True;continue
   target=str(Path(policy_root)/target);edge['resolved_path']=target
  if d.kind=='includedir':
   directory=Path(target)
   if not directory.exists():missing.append(dict(path=target,kind=d.kind));continue
   fd=reader.open_absolute(target,directory=True)
   try:
    entries=sorted(os.listdir(fd));assert len(entries)<=128;directories[target]=entries
   finally:os.close(fd)
   for name in entries:
    if name.endswith('.conf'):visit(str(directory/name))
  elif d.kind in ('include','selinux-include'):
   try:visit(target)
   except FileNotFoundError:
    if not d.optional:raise
    missing.append(dict(path=target,kind=d.kind,optional=True))
 stack.remove(path)
meta=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),broker_pid=pid(),packages=run(['rpm','-q','dbus-broker','dbus-1']),source_sha256={name:hashlib.sha256((BASE/name).read_bytes()).hexdigest() for name in ('native.py','dependencies.py','namespace.py','coordinator.py')},binaries={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/usr/bin/dbus-broker','/usr/bin/dbus-broker-launch')})
manager=int(meta['broker_pid']);meta['launcher_cmdline']=Path('/proc',str(manager),'cmdline').read_bytes().split(b'\0')[:-1];meta['launcher_cmdline']=[s.decode() for s in meta['launcher_cmdline']]
assert meta['launcher_cmdline']==['/usr/bin/dbus-broker-launch','--scope','system','--audit']
assert not any(n.startswith(PREFIX) for n in names())
before_names=names();before_accounts={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path('/etc/passwd'),Path('/etc/group'),Path('/etc/pam.d/systemd-user'))}
created_dirs=[];created_files=[];results=[];passed=False;error=None
try:
 visit('/usr/share/dbus-1/system.conf')
 record('actual-launcher-and-package-bound',cmdline=meta['launcher_cmdline'],packages=meta['packages'])
 record('configuration-dependency-graph-indexed',file_count=len(files),edge_count=len(edges),policy_root=policy_root,selinux_enabled=enabled)
 assert '/usr/share/dbus-1/system.d' in directories and '/etc/dbus-1/system.d' in directories
 record('vendor-policy-tree-outside-prior-guard-detected',entries=len(directories['/usr/share/dbus-1/system.d']))
 assert any(p['path']=='/etc/dbus-1/system-local.conf' for p in missing)
 record('optional-missing-override-retained-in-inventory',missing=missing)
 # Upstream v36 candidates plus negative probes for paths used in later versions.
 for index,root in enumerate(('/usr/local/share/dbus-1/system-services','/lib/dbus-1/system-services','/etc/dbus-1/system-services','/run/dbus-1/system-services','/usr/share/dbus-1/system-services')):
  path=Path(root);canonical=path.resolve();assert str(canonical).startswith(('/usr/','/etc/','/run/'))
  absent=[];p=canonical
  while not p.exists():absent.append(p);p=p.parent
  for directory in reversed(absent):directory.mkdir(mode=0o755);created_dirs.append(directory)
  name=PREFIX+'Directory'+str(index);file=canonical/(name+'.service');assert not file.exists() and not file.is_symlink()
  file.write_text('[D-BUS Service]\nName='+name+'\nUser=root\nExec=/usr/bin/false\n');file.chmod(0o644);created_files.append(file)
  reload();loaded=name in names();result=dict(path=root,canonical=str(canonical),loaded=loaded)
  results.append(result);record('actual-source-directory-probe-'+str(index),**result)
  file.unlink();created_files.remove(file);reload();assert name not in names()
  for directory in absent:directory.rmdir();created_dirs.remove(directory)
 # Actual distro binary, not an assumption from upstream main.
 assert results[0]['loaded'] and results[1]['loaded'] and results[4]['loaded']
 record('additional-activation-roots-confirmed-without-executing-payloads',positive=[x['path'] for x in results if x['loaded']],negative=[x['path'] for x in results if not x['loaded']])
 for path,row in files.items():assert hashlib.sha256(read(path)).hexdigest()==row['sha256']
 assert before_accounts=={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in before_accounts}
 record('configuration-pam-and-account-bytes-preserved')
 assert pid()==meta['broker_pid'] and names()==before_names
 record('shared-broker-pid-and-original-activatable-set-preserved',broker_pid=pid())
 passed=True
except BaseException as e:error=str(e);raise
finally:
 for file in reversed(created_files):file.unlink(missing_ok=True)
 for directory in reversed(created_dirs):directory.rmdir()
 reload()
 cleanup=dict(passed=pid()==meta['broker_pid'] and names()==before_names and not any(n.startswith(PREFIX) for n in names()),broker_pid=pid(),names_preserved=names()==before_names,created_paths_absent=all(not Path(x).exists() for x in created_dirs+created_files))
 row=dict(passed=passed and cleanup['passed'],error=error,checks=checks,metadata=meta,files=files,edges=edges,missing=missing,includedirs=directories,directory_probes=results,cleanup=cleanup,full_account_protection=False,global_source_coverage_qualified=False,configuration_semantics_qualified=False,loaded_configuration_identity_qualified=False)
 (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(dict(passed=row['passed'],checks=len(checks))));assert cleanup['passed']
