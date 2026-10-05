from pathlib import Path
import os,subprocess,hashlib,json,shlex
assert os.geteuid()==0
assert {'lyra.parental-identity-test=1','lyra.parental-selinux-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/release-identity-test');checks=[]
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90)
 row=dict(args=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr);assert p.returncode==0,row;return row
def record(name,**kwargs):
 checks.append(dict(name=name,passed=True,**kwargs));print(json.dumps(checks[-1]),flush=True)
def data():return dict((k,shlex.split(v)[0]) for k,v in (line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if line and not line.startswith('#')))
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
assert subprocess.run(['rpm','-q','lyra-release'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode!=0
before=digest('/usr/lib/os-release');link=os.readlink('/etc/os-release')
record('package-install',rpm=run(['rpm','-Uvh',str(BASE/'lyra-release.rpm')]))
assert data()['PRETTY_NAME']=='Lyra OS 1.1' and not Path('/etc/os-release').is_symlink() and digest('/usr/lib/os-release')==before
record('initial-trigger-replaces-link-without-changing-vendor',identity=data())
d=data();d.update(BUILD_ID='lyra-trigger-rehearsal',IMAGE_ID='lyra-desktop',IMAGE_VERSION='alpha8-test')
Path('/etc/os-release').write_text(''.join(k+'='+json.dumps(v)+'\n' for k,v in d.items()))
run(['/usr/libexec/lyra-release-identity'])
record('actual-leap-release-transaction',rpm=run(['rpm','-Uvh','--oldpackage','--replacepkgs',str(BASE/'Leap-release.rpm')]))
assert data()['PRETTY_NAME']=='Lyra OS 1.1' and data()['LOGO']=='distributor-logo-lyra' and data()['BUILD_ID']=='lyra-trigger-rehearsal' and data()['IMAGE_VERSION']=='alpha8-test'
record('base-update-reapplies-branding-and-preserves-image-metadata',identity=data(),vendor_sha256=digest('/usr/lib/os-release'))
record('second-base-reinstallation',rpm=run(['rpm','-Uvh','--replacepkgs',str(BASE/'Leap-release.rpm')]))
assert data()['PRETTY_NAME']=='Lyra OS 1.1' and data()['IMAGE_VERSION']=='alpha8-test'
record('package-removal',rpm=run(['rpm','-e','lyra-release']))
assert Path('/etc/os-release').is_symlink() and os.readlink('/etc/os-release')==link and data()['ID']=='opensuse-leap' and not Path('/var/lib/lyra-release/identity-state.json').exists()
record('removal-restores-original-link',identity=data())
row=dict(passed=True,checks=checks,fixture_rpms={p.name:digest(p) for p in BASE.glob('*.rpm')},disk_is_disposable_overlay=True,host_changed=False)
(BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(row))
