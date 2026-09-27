"""Build the exact SUSE source with one upstream fix, only in the marked VM."""
import hashlib,json,pathlib,subprocess
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
rows=[]
def run(args,cwd=None):
    r=subprocess.run(args,cwd=cwd,capture_output=True,text=True,timeout=300)
    rows.append(dict(argv=args,cwd=str(cwd) if cwd else None,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
    P('/root/shortcuts-portal-build.json').write_text(json.dumps(rows,indent=2))
    assert r.returncode==0,rows[-1]
    return r.stdout
signature=run(['rpm','-K','/root/shortcuts-portal-devel.rpm'])
assert 'signatures OK' in signature
run(['rpm','-Uvh','/root/shortcuts-portal-devel.rpm'])
workspace=P('/root/shortcuts-portal-source');workspace.mkdir()
run(['tar','-xf','/root/shortcuts-portal-source.tar.zst','-C',str(workspace)])
source=workspace/'xdg-desktop-portal-gnome-48.0'
run(['tar','-xf','/root/shortcuts-libgxdp.tar.zst','-C',str(source/'subprojects')])
subproject=source/'subprojects/libgxdp'
if subproject.exists():subproject.rmdir()
(source/'subprojects/libgxdp-0.gitmodule').rename(subproject)
run(['patch','--batch','--fuzz=0','-p1','-i','/root/globalshortcuts-success.patch'],cwd=source)
run(['meson','setup','/root/shortcuts-portal-build',str(source),'--prefix=/usr','--libdir=lib64','--buildtype=debugoptimized','--wrap-mode=nodownload'])
run(['meson','compile','-C','/root/shortcuts-portal-build','-j','2'])
binary=P('/root/shortcuts-portal-build/src/xdg-desktop-portal-gnome')
rows.append(dict(binary=str(binary),sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),installed=False))
P('/root/shortcuts-portal-build.json').write_text(json.dumps(rows,indent=2))
print(json.dumps(rows[-1]))
