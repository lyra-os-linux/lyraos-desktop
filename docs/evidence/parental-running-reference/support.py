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
BASE=Path('/root/running-reference-test');BASE.mkdir(mode=0o700,exist_ok=True)
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
