from pathlib import Path
import hashlib,json,os,subprocess
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/source-set-test');result=json.loads((BASE/'result.json').read_text())
paths=['/etc/dbus-1/system-local.conf','/usr/local/share/dbus-1/system-services','/usr/lib/dbus-1/system-services','/usr/share/dbus-1/system.d/lyra-source-set-test.conf',str(BASE/'sources.lock')]
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0;return p.stdout
pid=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()
row=dict(absent={p:not Path(p).exists() and not Path(p).is_symlink() for p in paths},configuration_preserved=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in result['configuration_hashes'].items()),accounts_and_pam_preserved=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in result['account_hashes'].items()),alias_preserved=os.readlink('/lib')=='usr/lib',broker_preserved=pid==result['metadata']['broker_pid'],broker_pid=pid)
row['passed']=all(row['absent'].values()) and all(row[k] for k in ('configuration_preserved','accounts_and_pam_preserved','alias_preserved','broker_preserved'))
(BASE/'restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
