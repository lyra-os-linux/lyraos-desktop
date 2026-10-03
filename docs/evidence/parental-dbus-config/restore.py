"""Independent read-only audit after all source-directory probes are removed."""
from pathlib import Path
import json,os,shlex,subprocess
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
base=Path('/root/dbus-config-audit');result=json.loads((base/'result.json').read_text())
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);assert p.returncode==0;return p.stdout
names=shlex.split(run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListActivatableNames']))[2:]
absent={}
for i,probe in enumerate(result['directory_probes']):
 path=Path(probe['canonical'])/('org.lyra.ConfigAudit.Directory'+str(i)+'.service')
 absent[str(path)]=not path.exists() and not path.is_symlink()
pid=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()
row=dict(absent=absent,unknown_loaded_absent=not any(n.startswith('org.lyra.ConfigAudit.') for n in names),broker_pid=pid,broker_preserved=pid==result['metadata']['broker_pid'],packages=run(['rpm','-q','dbus-broker','dbus-1']))
row['passed']=all(absent.values()) and row['unknown_loaded_absent'] and row['broker_preserved']
(base/'restored.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row));assert row['passed']
