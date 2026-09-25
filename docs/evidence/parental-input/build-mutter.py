"""Apply the incremental data-buffer patch after the XWayland milestone build."""
import hashlib,json,pathlib,subprocess
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
root=P('/root/mutter-patched')
patch=P('/root/mutter-shared-data.patch').read_bytes()
rows=[]
def run(args,**kwargs):
 p=subprocess.run(args,capture_output=True,timeout=120,**kwargs)
 rows.append(dict(argv=args,rc=p.returncode,stdout=p.stdout.decode(),stderr=p.stderr.decode()))
 assert p.returncode==0,rows[-1]
run(['patch','-p1','--forward','--batch'],cwd=root,input=patch)
run(['ninja','-C','/root/mutter-build','-j2','src/libmutter-16.so.0.0.0'])
run(['chrpath','-r','/usr/lib64/mutter-16','/root/mutter-build/src/libmutter-16.so.0.0.0'])
print(json.dumps(dict(commands=rows,source_sha256=hashlib.sha256((root/'src/core/meta-anonymous-file.c').read_bytes()).hexdigest(),library_sha256=hashlib.sha256(P('/root/mutter-build/src/libmutter-16.so.0.0.0').read_bytes()).hexdigest()),indent=2))
