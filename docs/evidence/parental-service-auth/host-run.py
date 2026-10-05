from pathlib import Path
import json,subprocess,hashlib
A=Path(__file__).resolve().parent
E=Path('/home/rodrigo/Git/LyraOS/worktrees/desktop-parental-registry-lifetime/docs/evidence')
OUT=E/'parental-service-auth'
def guest(*args):
 p=subprocess.run(['python3',str(A/'vm.py'),'virtualization','cmd',*args],capture_output=True,text=True,timeout=240)
 assert p.stdout,p.stderr
 return json.loads(p.stdout)
def checked(name,*args):
 row=guest(*args);(OUT/name).write_text(json.dumps(row,indent=2)+'\n');assert row['rc']==0,row;return row
checked('guard.json','python3','-c',"from pathlib import Path;import os,json;assert os.geteuid()==0;assert 'lyra.parental-identity-test=1' in Path('/proc/cmdline').read_text().split();assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test';p=Path('/root/lyra-service-auth-test');assert not p.exists();p.mkdir(mode=0o700);print(json.dumps(dict(guard=True)))")
files={'parental-coordinator':['coordinator.py'],'parental-ordinary-withdrawal':['withdrawal.py'],'parental-operation-journal':['operations.py'],'parental-inventory-gate':['inventory.py'],'parental-registry-barrier':['writer.py'],'parental-service-classifier':['classifier.py'],'parental-service-withdrawal':['binding.py'],'parental-service-auth':['fixture.py','server.py','client.py','guest.py']}
hashes={}
for folder,names in files.items():
 for name in names:
  source=E/folder/name;hashes[name]=hashlib.sha256(source.read_bytes()).hexdigest()
  subprocess.run(['python3',str(A/'host.py'),'push',str(source),'/root/lyra-service-auth-test/'+name],check=True,capture_output=True)
checked('source-hashes.json','python3','-c',"from pathlib import Path;import hashlib,json;expected="+repr(hashes)+";actual={n:hashlib.sha256((Path('/root/lyra-service-auth-test')/n).read_bytes()).hexdigest() for n in expected};assert actual==expected;print(json.dumps(actual))")
row=guest('python3','/root/lyra-service-auth-test/guest.py');(OUT/'execution.json').write_text(json.dumps(row,indent=2)+'\n')
subprocess.run(['python3',str(A/'host.py'),'pull','/root/lyra-service-auth-test/result.json',str(OUT/'result.json')],check=True,capture_output=True)
assert row['rc']==0,row
print('PASS: real system D-Bus and Polkit cases; fixture cleanup confirmed',flush=True)
