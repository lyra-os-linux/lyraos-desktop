"""Independent preservation/absence checks after the reserved running fixture."""
from pathlib import Path
import hashlib,json,os,subprocess
from namespace import Namespace
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/running-reference-test');result=json.loads((BASE/'result.json').read_text());assert result['passed']
reader=Namespace(['/usr/lib/systemd/system'],str(BASE/'unused.lock'))
def fingerprint(path):
 fd=reader.open_absolute(path)
 try:
  before=os.fstat(fd);assert before.st_size<=32*1024*1024;data=bytearray()
  while True:
   chunk=os.read(fd,65536)
   if not chunk:break
   data.extend(chunk);assert len(data)<=32*1024*1024
  assert len(data)==before.st_size and reader.stamp(os.fstat(fd))==reader.stamp(before)
  return list(reader.stamp(before))+[hashlib.sha256(data).hexdigest()]
 finally:os.close(fd)
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0,(args,p.stderr);return p.stdout
reserved=['/usr/lib/systemd/system/lyra-parental-running-probe.service','/usr/libexec/lyra-parental-running-probe',str(BASE/'unused.lock')]
prior=json.loads(Path('/root/service-catalog-test/result.json').read_text())
oldunits=json.loads(Path('/root/systemd-reference-test/result.json').read_text())
state=dict(line.split('=',1) for line in run(['systemctl','show','lyra-parental-running-probe.service','-p','LoadState','-p','ActiveState','-p','MainPID','-p','ControlGroup']).splitlines())
processes=[]
for path in Path('/proc').iterdir():
 if not path.name.isdecimal():continue
 try:
  raw=(path/'cmdline').read_bytes();cgroup=(path/'cgroup').read_text()
  if '/lyra-parental-running-probe.service' in cgroup or raw.startswith(b'/usr/libexec/lyra-parental-running-probe\0'):processes.append(int(path.name))
 except (FileNotFoundError,ProcessLookupError):pass
row=dict(absent={p:not Path(p).exists() and not Path(p).is_symlink() for p in reserved},accounts_and_pam_preserved=all(fingerprint(p)==value for p,value in result['original_accounts'].items()),declarations_preserved=all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['digest'] for x in prior['original_declarations']),previous_accepted_unit_files_preserved=all(fingerprint(path)==value for ref in oldunits['references'] for path,value in ref['fingerprints']),broker_preserved=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()==result['metadata']['broker_pid'],unit_state=state,reserved_processes=processes,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
row['passed']=all(row['absent'].values()) and not processes and state['MainPID']=='0' and state['ControlGroup']=='' and state['LoadState']=='not-found' and state['ActiveState']=='inactive' and all(row[k] for k in ('accounts_and_pam_preserved','declarations_preserved','previous_accepted_unit_files_preserved','broker_preserved'))
(BASE/'restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
