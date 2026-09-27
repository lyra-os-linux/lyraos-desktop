"""Build the minimal backport RPM only in the marked disposable VM."""
import hashlib, json, pathlib, shutil, subprocess
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert P('/sys/block/vda/serial').read_text().strip()=='lyra-virtualization-'
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
top=P('/root/portal-rpmbuild');top.mkdir(exist_ok=True)
rows=[]
def run(args,timeout=600):
 r=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 rows.append(dict(argv=args,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
 P('/root/portal-rpm-build.json').write_text(json.dumps(rows,indent=2))
 assert r.returncode==0,rows[-1]
 return r.stdout
source=P('/root/portal-original.src.rpm')
assert hashlib.sha256(source.read_bytes()).hexdigest()=='fe04ca23fac46c3efdea0d0cf49c4a7d3cc3917083e5c11a8a65bca19c4e124f'
assert 'signatures OK' in run(['rpm','-K',str(source)])
run(['rpm','-i','--define','_topdir '+str(top),str(source)])
shutil.copyfile('/root/portal-rpm.spec',top/'SPECS/xdg-desktop-portal-gnome.spec')
patch=P('/root/globalshortcuts-success.patch')
assert hashlib.sha256(patch.read_bytes()).hexdigest()=='fec1059820db03ee20378cf5e3c7b550c36149b0291fb40df0ad77e41ae3993a'
shutil.copyfile(patch,top/'SOURCES/globalshortcuts-success.patch')
run(['rpmbuild','-ba','--define','_topdir '+str(top),'--define','_smp_mflags -j2',str(top/'SPECS/xdg-desktop-portal-gnome.spec')])
artifacts=[]
for file in sorted(top.glob('**/*.rpm')):
 artifacts.append(dict(path=str(file),sha256=hashlib.sha256(file.read_bytes()).hexdigest(),size=file.stat().st_size,nevra=run(['rpm','-qp','--qf','%{NEVRA}',str(file)])))
P('/root/portal-rpm-artifacts.json').write_text(json.dumps(artifacts,indent=2))
print(json.dumps(artifacts,indent=2))
