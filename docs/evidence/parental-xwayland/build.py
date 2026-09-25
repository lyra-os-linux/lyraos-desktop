import pathlib,subprocess,json,tarfile
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
rows=[]
def run(args):
 r=subprocess.run(args,capture_output=True,text=True,timeout=400)
 rows.append(dict(argv=args,rc=r.returncode,stdout=r.stdout,stderr=r.stderr));P('/root/xwayland-build.json').write_text(json.dumps(rows,indent=2))
 assert r.returncode==0,rows[-1]
with tarfile.open('/root/xwayland-patched.tar.gz') as t:t.extractall('/root',filter='data')
run(['meson','setup','/root/xwayland-build','/root/xwayland-patched','--prefix=/usr','--sysconfdir=/etc','--localstatedir=/var','-Dglamor=true','-Dxvfb=true','-Dglx=true','-Dxdmcp=true','-Dxdm-auth-1=true','-Dsecure-rpc=true','-Dipv6=true','-Dinput_thread=true','-Dvendor_name=SUSE LINUX','-Dvendor_name_short=openSUSE','-Dvendor_web=https://www.opensuse.org','-Dlisten_tcp=false','-Dlisten_unix=true','-Dlisten_local=true','-Dxf86bigfont=true','-Dscreensaver=true','-Dxres=true','-Dxace=true','-Dxselinux=false','-Dxinerama=true','-Dxcsecurity=true','-Dxv=true','-Dmitshm=true','-Dsha1=libcrypto','-Ddri3=true','-Dxwayland-path=/usr/bin','-Ddtrace=false','-Dlibunwind=false','-Dxkb_dir=/usr/share/X11/xkb','-Dxkb_output_dir=/var/lib/xkb/compiled'])
run(['ninja','-C','/root/xwayland-build','-j2','hw/xwayland/Xwayland'])
print(json.dumps(dict(passed=True,commands=len(rows)),indent=2))
