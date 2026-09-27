"""Real zypper transitions, only in the marked disposable parental VM.

Run as a bounded systemd service with ExecStopPost invoking `recover`.
All four local RPMs must already exist; no artifact URL is trusted at execution.
"""
import hashlib,json,os,pathlib,subprocess,sys
from policy import NAME, SUSE, STAGING, validate_plan
P=pathlib.Path
ROOT=P('/root/portal-transition-state')
STATE=ROOT/'active.json'
REPORT=ROOT/'commands.json'
PACKAGES={
 '/root/portal-original.rpm':'6613e7d4f1b3acd5c0f9a36636ec61e9cb57b6cc902b52d1e550b8605cfe486b',
 '/root/portal-original-lang.rpm':'1af37ebcaf15c3d0ba30d59fd3643ccfc5414b274005b67ca0289c2ba81ce0ab',
 '/root/portal-staging.rpm':'9e7f6622e12cc8c343f772b5900d4ca7e4be01c9a20ef9477cf24373e55b1670',
 '/root/portal-staging-lang.rpm':'ba84d6486f3b5907c86e0a38e17d93e939e0dbb674cd3ea4754deac256f50a28',
}
rows=[]
def write(path,data):
 tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2)+'\n');os.replace(tmp,path)
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90,env={**os.environ,'LC_ALL':'C.UTF-8'})
 rows.append(dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr));write(REPORT,rows)
 if p.returncode:raise RuntimeError(rows[-1])
 return p.stdout

def inventory():
 return sorted(run(['rpm','-qa','--qf','%{NAME}\t%{ARCH}\t%{VERSION}-%{RELEASE}\t%{VENDOR}\n']).splitlines())

def versions(names):
 result={}
 for name in names:
  edition,vendor=run(['rpm','-q','--qf','%{VERSION}-%{RELEASE}\n%{VENDOR}',name]).splitlines()
  result[name]=[edition,vendor]
 return result

def assert_target(names,target):
 assert all(tuple(v)==target for v in versions(names).values())
 assert run(['rpm','-V',*names])==''

def validate_inputs():
 assert os.geteuid()==0
 assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
 assert P('/sys/block/vda/serial').read_text().strip()=='lyra-virtualization-'
 assert not P('/root/lyra-xwayland-recovery/active.json').exists()
 for unit in ['gdm','user@1002.service','user@1003.service']:
  assert subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip()=='inactive'
 for path,digest in PACKAGES.items():
  assert hashlib.sha256(P(path).read_bytes()).hexdigest()==digest,path
 assert hashlib.sha256(P('/root/portal-staging.key').read_bytes()).hexdigest()=='66b8cda88e6b5d707e6f9d75a9579ab785daebf33b63e39d9cb86335294e7a25'

def config_hashes():
 paths=list(P('/etc/zypp/repos.d').glob('*.repo'))+[P('/etc/zypp/zypp.conf')]
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None for p in paths}

def recover():
 if not STATE.exists():return
 baseline=json.loads(STATE.read_text())
 # Signed original is used only for emergency fixture recovery; successful
 # rounds below return via zypper, not this fallback.
 installed_names=[NAME]
 if subprocess.run(['rpm','-q',NAME+'-lang'],capture_output=True).returncode==0:
  installed_names.append(NAME+'-lang')
 if any(tuple(v)!=SUSE for v in versions(installed_names).values()):
  files=['/root/portal-original.rpm']
  if len(installed_names)==2:
   files.append('/root/portal-original-lang.rpm')
  run(['rpm','-Uvh','--oldpackage',*files])
 if not baseline['lang_present'] and subprocess.run(['rpm','-q',NAME+'-lang'],capture_output=True).returncode==0:
  run(['rpm','-e',NAME+'-lang'])
 added=set(run(['rpm','-qa','gpg-pubkey']).splitlines())-set(baseline['keys'])
 assert all(k.startswith('gpg-pubkey-7edca82e-') for k in added)
 if added:run(['rpm','-e',*sorted(added)])
 assert set(run(['rpm','-qa','gpg-pubkey']).splitlines())==set(baseline['keys'])
 assert inventory()==baseline['inventory']
 assert config_hashes()==baseline['config_hashes']
 assert_target([NAME],SUSE)
 assert hashlib.sha256(P('/usr/libexec/'+NAME).read_bytes()).hexdigest()==baseline['binary_sha256']
 write(ROOT/'restored.json',dict(restored=True,inventory_equal=True,config_equal=True,keys_equal=True))
 STATE.unlink()

def transition(tag,names,target,noop=False):
 before_inventory=inventory();before=versions(names);after={name:list(target) for name in names}
 prefix='original' if target==SUSE else 'staging'
 files=['/root/portal-'+prefix+('-lang' if name.endswith('-lang') else '')+'.rpm' for name in names]
 args=['zypper','--xmlout','--non-interactive','--no-refresh','install','--no-recommends','--allow-vendor-change']
 if target==SUSE:args.append('--oldpackage')
 dry=run(args+['--dry-run',*files])
 changed=validate_plan(dry,before,after)
 assert (not changed)==noop
 # The whole installed inventory and pinned local files must still match the
 # checked plan. No repository refresh or solver-answer override is permitted.
 assert inventory()==before_inventory
 for f in files:assert hashlib.sha256(P(f).read_bytes()).hexdigest()==PACKAGES[f]
 applied=run(args+files)
 assert_target(names,target)
 after_inventory=inventory()
 assert [r for r in before_inventory if r.split('\t')[0] not in names]==[r for r in after_inventory if r.split('\t')[0] not in names]
 if noop:assert before_inventory==after_inventory
 write(ROOT/(tag+'.json'),dict(tag=tag,before=before,after=after,before_inventory=before_inventory,after_inventory=after_inventory,changed=changed,dry_run=dry,applied=applied,passed=True))

if __name__=='__main__':
 validate_inputs();ROOT.mkdir(mode=0o700,exist_ok=True)
 if REPORT.exists():rows=json.loads(REPORT.read_text())
 if sys.argv[1:] == ['recover']:recover();raise SystemExit(0)
 assert not sys.argv[1:] and not STATE.exists() and not rows
 assert_target([NAME],SUSE)
 assert subprocess.run(['rpm','-q',NAME+'-lang'],capture_output=True).returncode==1
 baseline=dict(lang_present=False,keys=run(['rpm','-qa','gpg-pubkey']).splitlines(),inventory=inventory(),config_hashes=config_hashes(),binary_sha256=hashlib.sha256(P('/usr/libexec/'+NAME).read_bytes()).hexdigest())
 write(STATE,baseline);write(ROOT/'baseline.json',baseline)
 try:
  run(['rpm','--import','/root/portal-staging.key'])
  for file in PACKAGES:
   assert 'signatures OK' in run(['rpmkeys','--checksig',file])
   metadata=run(['rpm','-qp','--qf','%{VERSION}-%{RELEASE}\n%{VENDOR}',file]).splitlines()
   assert tuple(metadata)==(SUSE if 'original' in file else STAGING)
  transition('main-upgrade',[NAME],STAGING)
  transition('main-idempotent',[NAME],STAGING,noop=True)
  transition('main-return',[NAME],SUSE)
  # Prepare the second ordinary installation shape (translations present).
  run(['rpm','-ivh','/root/portal-original-lang.rpm'])
  transition('translated-upgrade',[NAME,NAME+'-lang'],STAGING)
  transition('translated-idempotent',[NAME,NAME+'-lang'],STAGING,noop=True)
  transition('translated-return',[NAME,NAME+'-lang'],SUSE)
 finally:recover()
 print('Six zypper rounds PASS; original inventory and configuration restored')
