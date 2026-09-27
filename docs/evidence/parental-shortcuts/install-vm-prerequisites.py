"""One-time addition of the image's official recording dependency to the old VM."""
import pathlib,subprocess,tarfile,json,hashlib
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
dest=P('/root/parental-gstreamer');dest.mkdir(exist_ok=True)
with tarfile.open('/root/parental-gstreamer.tar') as archive:archive.extractall(dest,filter='data')
files=sorted(dest.glob('*.rpm'));assert len(files)==11
rows=[]
for file in files:
 p=subprocess.run(['rpm','--checksig',str(file)],capture_output=True,text=True)
 assert p.returncode==0 and 'signatures OK' in p.stdout and 'NOKEY' not in p.stdout and 'NOT OK' not in p.stdout,(p.stdout,p.stderr)
 rows.append(dict(file=file.name,sha256=hashlib.sha256(file.read_bytes()).hexdigest(),signature=p.stdout))
p=subprocess.run(['zypper','--non-interactive','--no-refresh','install','--no-recommends',*map(str,files)],capture_output=True,text=True,timeout=90)
report=dict(packages=rows,rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
P('/root/parental-gstreamer-install.json').write_text(json.dumps(report,indent=2))
assert p.returncode==0,report
print(json.dumps(report,indent=2))
