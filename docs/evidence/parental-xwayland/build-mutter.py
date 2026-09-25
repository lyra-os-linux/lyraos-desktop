import pathlib,subprocess,json,tarfile
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
rows=[]
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=600)
 rows.append(dict(argv=args,rc=r.returncode,stdout=r.stdout,stderr=r.stderr));P('/root/mutter-build.json').write_text(json.dumps(rows,indent=2))
 assert r.returncode==0,dict(argv=args,rc=r.returncode,stdout=r.stdout[-3000:],stderr=r.stderr[-3000:])
with tarfile.open('/root/mutter-patched.tar.gz') as t:t.extractall('/root',filter='data')
run(['meson','setup','/root/mutter-build','/root/mutter-patched','--prefix=/usr','--libdir=lib64','--sysconfdir=/etc','--localstatedir=/var','-Degl_device=true','-Dwayland_eglstream=true','-Dcogl_tests=false','-Dclutter_tests=false','-Dtests=disabled','-Dinstalled_tests=false','-Dxwayland_initfd=auto','-Dprofiler=false'])
run(['ninja','-C','/root/mutter-build','-j2','src/libmutter-16.so.0.0.0'])
run(['chrpath','-r','/usr/lib64/mutter-16','/root/mutter-build/src/libmutter-16.so.0.0.0'])
print(json.dumps(dict(passed=True,commands=len(rows)),indent=2))
