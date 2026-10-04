"""Independent read-only preservation check; no manager-cache rollback claim."""
from pathlib import Path
import hashlib,json,os,subprocess
from namespace import Namespace
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/systemd-reference-test');r=json.loads((BASE/'result.json').read_text());assert r['passed']
reader=Namespace(['/usr/lib/systemd/system'],str(BASE/'unused.lock'))
def fingerprint(path):
 fd=reader.open_absolute(path)
 try:
  s=os.fstat(fd);assert s.st_size<=32*1024*1024;data=bytearray()
  while True:
   chunk=os.read(fd,65536)
   if not chunk:break
   data.extend(chunk);assert len(data)<=32*1024*1024
  assert len(data)==s.st_size and reader.stamp(os.fstat(fd))==reader.stamp(s)
  return list(reader.stamp(s)) + [hashlib.sha256(data).hexdigest()]
 finally:os.close(fd)
p=subprocess.run(['systemctl','show','dbus.service','-p','MainPID','--value'],capture_output=True,text=True,timeout=30);assert p.returncode==0
prior=json.loads(Path('/root/service-catalog-test/result.json').read_text())
row=dict(references_preserved=all(fingerprint(path)==value for ref in r['references'] for path,value in ref['fingerprints']),accounts_and_pam_preserved=all(fingerprint(path)==value for path,value in r['original_accounts'].items()),declarations_preserved=all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['digest'] for x in prior['original_declarations']),broker_preserved=p.stdout.strip()==r['metadata']['broker_pid'],broker_pid=p.stdout.strip(),unused_lock_absent=not (BASE/'unused.lock').exists() and not (BASE/'unused.lock').is_symlink(),source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),manager_cache_rollback_claimed=False)
row['passed']=all(row[k] for k in ('references_preserved','accounts_and_pam_preserved','declarations_preserved','broker_preserved','unused_lock_absent'))
(BASE/'restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
