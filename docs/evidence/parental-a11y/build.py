"""Build only the diagnostic native X11 hook from the patched official tree."""
import pathlib,subprocess,json
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
rows=[]
for cmd in [
 ['meson','setup','/root/atspi-hook-build','/root/at-spi2-core-2.58.7','--prefix=/usr','--sysconfdir=/usr/etc','--libexecdir=/usr/libexec','-Dgtk2_atk_adaptor=false','-Dintrospection=disabled','-Ddocs=false','-Dx11=enabled'],
 ['ninja','-C','/root/atspi-hook-build','bus/00-at-spi']]:
 r=subprocess.run(cmd,capture_output=True,text=True,timeout=90)
 rows.append(dict(argv=cmd,rc=r.returncode,stdout=r.stdout,stderr=r.stderr))
 print(json.dumps(rows[-1]),flush=True)
 assert r.returncode==0
print(json.dumps(rows,indent=2))
