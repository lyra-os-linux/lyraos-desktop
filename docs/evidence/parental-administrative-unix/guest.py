"""Real profile/groups effects on one fictitious account in a guarded VM."""
import json,os,shutil,subprocess,sys,hashlib,grp,pwd
from pathlib import Path
import fixture as f
base=f.load('administrative_base','guard.py')
p=f.load('administrative_parameters','parameters.py')
TARGET=f.IDENTITIES[1002]['user'];PEER=f.IDENTITIES[1000]['user']
assert TARGET=='ordinaryuser' and PEER=='installeduser'
assert not any(x.isdigit() and Path('/proc',x,'status').exists() and
 str(1002) in Path('/proc',x,'status').read_text().split('Uid:')[-1].splitlines()[0].split()
 for x in os.listdir('/proc') if x.isdigit())
PATHS=[Path('/etc')/name for name in ('passwd','group','gshadow','shadow','passwd-','group-','gshadow-','shadow-')]
original={str(path):dict(data=path.read_bytes(),uid=path.stat().st_uid,gid=path.stat().st_gid,mode=path.stat().st_mode&0o777) if path.exists() else None for path in PATHS}
before=f.system_state()
executables={name:hashlib.sha256(Path(name).read_bytes()).hexdigest() for name in ('/usr/sbin/usermod','/usr/bin/gpasswd')}
backup=f.BASE/'account-backup';assert not backup.exists();backup.mkdir(mode=0o700)
for path,row in original.items():
 if row is not None:
  saved=backup/Path(path).name;saved.write_bytes(row['data']);saved.chmod(0o600)
def hashes():return {str(path):hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None for path in PATHS}
initial_hashes=hashes()
def members(user):return sorted(g.gr_name for g in grp.getgrall() if user in g.gr_mem)
peer_before=dict(identity=f.identify(1000),profile=pwd.getpwnam(PEER).pw_gecos,groups=members(PEER))
identity=f.identify(1002)
assert 'wheel' not in members(TARGET)
checks=[];commands=[];noops=[];error=None;passed=False
f.DATA.mkdir(mode=0o700)
def check(name,condition):
 assert condition,name
 checks.append(name)
def fixture(name):
 obj=f.Fixture(f.DATA/name,create=True)
 sealed=p.SealedGuard(base.Guard(obj.bridge),lambda name:grp.getgrnam(name).gr_gid)
 return obj,sealed

def apply(method,account,params):
 assert account.identity.uid==1002 and account.identity.user==TARGET
 args=p.command(f.c,method,account,params)
 assert args[0] in executables
 for lock in (active.catalog_dir/'catalog.lock',active.inventory_dir/'.inventory-1002.lock',active.ledger/'.gate-1002.lock'):
  try:
   with f.exclusive(lock):pass
  except BlockingIOError:pass
  else:raise AssertionError('missing lease '+lock.name)
 if method=='SetAdmin' and ('wheel' in members(TARGET))==params.is_admin:
  noops.append(dict(method=method,is_admin=params.is_admin));return
 row=subprocess.run(args,capture_output=True,text=True,timeout=10)
 commands.append(dict(argv=list(args),returncode=row.returncode))
 assert row.returncode==0,(row.returncode,row.stderr)
 assert f.identify(1002)==identity

def plan(obj,guard,method,values):return guard.plan(':1.20','a'*32,1,method,values)
def execute(obj,guard,planned,auth=None):
 return guard.execute(':1.20',planned.base.admission.identifier,auth or obj.authorize,apply)
try:
 active,sealed=fixture('profile')
 values=dict(full_name='Lyra fixture $(literal)',groups=['users'],is_admin=False)
 planned=plan(active,sealed,'UpdateUser',values)
 values['full_name']='Changed after plan';values['groups'].append('wheel');values['is_admin']=True
 check('profile dispatch',execute(active,sealed,planned)=='OrdinaryMutationDispatched')
 check('profile exact sealed name',pwd.getpwnam(TARGET).pw_gecos=='Lyra fixture $(literal)')
 check('profile exact sealed supplementary groups',members(TARGET)==['users'])
 check('primary identity preserved',f.identify(1002)==identity)
 active,sealed=fixture('grant')
 planned=plan(active,sealed,'SetAdmin',dict(is_admin=True))
 execute(active,sealed,planned)
 check('admin grant only adds wheel',members(TARGET)==['users','wheel'])
 planned=plan(active,sealed,'SetAdmin',dict(is_admin=True))
 before_repeat=hashes();execute(active,sealed,planned)
 check('already-admin no-op files unchanged',hashes()==before_repeat)
 active,sealed=fixture('revoke')
 planned=plan(active,sealed,'SetAdmin',dict(is_admin=False));execute(active,sealed,planned)
 check('admin revoke preserves other groups',members(TARGET)==['users'])
 planned=plan(active,sealed,'SetAdmin',dict(is_admin=False));before_repeat=hashes();execute(active,sealed,planned)
 check('already-nonadmin no-op files unchanged',hashes()==before_repeat)
 active,sealed=fixture('denied')
 planned=plan(active,sealed,'SetAdmin',dict(is_admin=True));before_denied=hashes();count=len(commands)
 try:execute(active,sealed,planned,lambda _:False)
 except f.c.Error as exc:assert exc.code=='Denied'
 else:raise AssertionError('denial missing')
 check('denial no Unix command or writes',count==len(commands) and before_denied==hashes())
 active,sealed=fixture('blocked')
 planned=plan(active,sealed,'SetAdmin',dict(is_admin=True));before_blocked=hashes();count=len(commands)
 def auth(payload):
  active.authorize(payload)
  with f.exclusive(active.ledger/'.gate-1002.lock'):
   f.atomic(active.ledger,'.deny-1002',b'fixture-negative-intent\n')
  return True
 try:execute(active,sealed,planned,auth)
 except f.c.Error as exc:assert exc.code=='Blocked'
 else:raise AssertionError('blocked dispatch')
 check('new barrier no Unix command or account writes',count==len(commands) and before_blocked==hashes())
 check('peer profile identity groups preserved',peer_before==dict(identity=f.identify(1000),profile=pwd.getpwnam(PEER).pw_gecos,groups=members(PEER)))
 check('passwd unrelated users preserved', [line for line in Path('/etc/passwd').read_bytes().splitlines() if not line.startswith(TARGET.encode()+b':')]==[line for line in original['/etc/passwd']['data'].splitlines() if not line.startswith(TARGET.encode()+b':')])
 check('shadow not changed',Path('/etc/shadow').read_bytes()==original['/etc/shadow']['data'])
 passed=True
except Exception as exc:error=repr(exc)
finally:
 f.guard()
 for path,row in original.items():
  file=Path(path)
  if row is None:file.unlink(missing_ok=True)
  elif not file.exists() or file.read_bytes()!=row['data']:
   file.write_bytes(row['data']);os.chown(file,row['uid'],row['gid']);file.chmod(row['mode'])
   fd=os.open(file,os.O_RDONLY);os.fsync(fd);os.close(fd)
 fd=os.open('/etc',os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 restored=hashes()==initial_hashes and f.system_state()==before
 assert backup.parent==f.BASE and f.DATA.parent==f.BASE
 shutil.rmtree(backup);shutil.rmtree(f.DATA)
 receipt=dict(passed=passed,error=error,checks=checks,commands=commands,noops=noops,
   account_hashes_before=initial_hashes,account_hashes_after=hashes(),state_before=before,
   state_after=f.system_state(),restored=restored,cleanup=not backup.exists() and not f.DATA.exists(),
   executables=executables,identity_before=identity,identity_after=f.identify(1002),
   real_unix_effects=True,real_polkit=False,production_integrated=False)
 (f.BASE/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert restored
print(json.dumps(dict(passed=passed,checks=len(checks),commands=len(commands),noops=len(noops),error=error,cleanup=receipt['cleanup'])))
sys.exit(0 if passed else 1)
