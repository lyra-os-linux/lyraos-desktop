from pathlib import Path
import hashlib,json,os,subprocess
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/service-catalog-test');r=json.loads((BASE/'result.json').read_text());prior=json.loads(Path('/root/source-set-test/result.json').read_text())
paths=['/usr/local/share/dbus-1/system-services','/usr/lib/dbus-1/system-services','/usr/share/dbus-1/system-services/org.lyra.CatalogProbe.Known.service',str(BASE/'sources.lock')]
p=subprocess.run(['systemctl','show','dbus.service','-p','MainPID','--value'],capture_output=True,text=True,timeout=30);assert p.returncode==0
row=dict(absent={p:not Path(p).exists() and not Path(p).is_symlink() for p in paths},definitions_preserved=all(hashlib.sha256(Path(x['path']).read_bytes()).hexdigest()==x['digest'] for x in r['original_declarations']),accounts_preserved=all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in r['account_hashes'].items()),pam_preserved=hashlib.sha256(Path('/etc/pam.d/systemd-user').read_bytes()).hexdigest()==prior['account_hashes']['/etc/pam.d/systemd-user'],alias_preserved=os.readlink('/lib')=='usr/lib',broker_preserved=p.stdout.strip()==r['metadata']['broker_pid'],broker_pid=p.stdout.strip())
row['passed']=all(row['absent'].values()) and all(row[k] for k in ('definitions_preserved','accounts_preserved','pam_preserved','alias_preserved','broker_preserved'))
(BASE/'restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
