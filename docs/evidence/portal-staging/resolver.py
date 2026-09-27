"""Dry-run the existing installed-system and image priorities, in the VM only."""
import json,pathlib,shutil,subprocess,sys
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert P('/sys/block/vda/serial').read_text().strip()=='lyra-virtualization-'
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
mode=sys.argv[1];assert mode in ['candidate','original']
name='xdg-desktop-portal-gnome'
original=P('/etc/zypp/repos.d/parental-official.repo');stage=P('/etc/zypp/repos.d/portal-staging-test.repo')
assert original.is_file() and not stage.exists()
backup=P('/root/portal-resolver-'+mode+'.repo');shutil.copy2(original,backup)
rows=[];output=P('/root/portal-resolver-'+mode+'.json')
def run(args,timeout=120):
 p=subprocess.run(args,capture_output=True,text=True,timeout=timeout)
 rows.append(dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr));output.write_text(json.dumps(rows,indent=2))
 assert p.returncode==0,rows[-1]
 return p.stdout
keys=set(run(['rpm','-qa','gpg-pubkey']).splitlines())
try:
 run(['rpm','--import','/root/portal-staging.key'])
 run(['zypper','--non-interactive','modifyrepo','--priority','20','parental-official'])
 stage.write_text('[portal-staging-test]\nname=Disposable signed portal solver test\nenabled=1\nautorefresh=0\nbaseurl=https://download.opensuse.org/repositories/home:/rodrigosbrito:/lyra:/staging/openSUSE_Leap_16.1/\npriority=90\ngpgcheck=1\n')
 run(['zypper','--non-interactive','refresh','portal-staging-test'],240)
 run(['zypper','--no-refresh','lr','-u'])
 installed=run(['rpm','-q','--qf','%{NEVRA}\n%{VENDOR}',name])
 assert ('lyra1' in installed)==(mode=='candidate'),installed
 base=['zypper','--xmlout','--non-interactive','--no-refresh']
 run(base+['update','--dry-run',name])
 run(base+['update','--dry-run','--repo','portal-staging-test',name])
 run(base+['install','--dry-run','--no-recommends','--allow-vendor-change','--from','portal-staging-test',name])
 # Installed-system normal priorities: detect whether a forced reinstall would
 # choose the official package. This is a dry run, never an actual downgrade.
 run(base+['install','--dry-run','--no-recommends','--force','--allow-vendor-change',name])
 run(['zypper','--non-interactive','modifyrepo','--priority','1','portal-staging-test'])
 run(base+['install','--dry-run','--no-recommends','--force','--allow-vendor-change',name])
finally:
 stage.unlink(missing_ok=True);shutil.copy2(backup,original)
 added=set(subprocess.check_output(['rpm','-qa','gpg-pubkey'],text=True).splitlines())-keys
 assert all(p.startswith('gpg-pubkey-7edca82e-') for p in added),added
 if added:subprocess.run(['rpm','-e',*sorted(added)],check=True)
 assert original.read_bytes()==backup.read_bytes() and not stage.exists()
 output.with_suffix('.restored.json').write_text(json.dumps(dict(restored=True,keys_restored=True)))
print(json.dumps(dict(mode=mode,passed=True,dry_runs=5)))
