"""Install/remove narrow fixture policies only in a guarded disposable VM."""
import hashlib,json,os,shutil,subprocess,sys,time,pwd,grp
from pathlib import Path
import fixture as f
import dbus
BASE=f.BASE
RUN=Path('/run/lyra-parental-dbus-test')
CONF=Path('/etc/dbus-1/system.d/lyra-parental-fixture.conf')
POLICY=Path('/usr/share/polkit-1/actions/org.lyraos.parental.fixture.policy')
RULE=Path('/etc/polkit-1/rules.d/00-lyra-parental-fixture.rules')
assert not any(p.exists() or p.is_symlink() for p in (RUN,CONF,POLICY,RULE,f.DATA))
BUS=dbus.SystemBus(private=True)
authority=dbus.Interface(BUS.get_object('org.freedesktop.PolicyKit1','/org/freedesktop/PolicyKit1/Authority'),'org.freedesktop.PolicyKit1.Authority')

def configs():
 dirs=['/etc/dbus-1/system.d','/usr/share/polkit-1/actions','/etc/polkit-1/rules.d']
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for d in dirs for p in sorted(Path(d).glob('*')) if p.is_file()}
def actions():return {str(row[0]) for row in authority.EnumerateActions('C')}
def wait_actions(present):
 deadline=time.monotonic()+15
 while True:
  found={'org.lyraos.parental.fixture.'+suffix for suffix in ('allow','deny','challenge')} <= actions()
  if found==present:return
  assert time.monotonic()<deadline,'polkit policy reload timeout'
  time.sleep(.1)
def reload():BUS.get_object('org.freedesktop.DBus','/org/freedesktop/DBus').ReloadConfig(dbus_interface='org.freedesktop.DBus')

def service(mode,case):
 log=(BASE/(case.name+'-server.log')).open('ab')
 process=subprocess.Popen([sys.executable,str(BASE/'server.py'),mode,str(case)],stdout=log,stderr=subprocess.STDOUT)
 processes.append(process)
 deadline=time.monotonic()+10
 while not (case/'ready').exists():
  assert process.poll() is None and time.monotonic()<deadline,(BASE/(case.name+'-server.log')).read_text()
  time.sleep(.05)
 return process

def stop(process):
 process.terminate();process.wait(timeout=10)

def client(mode,user='installeduser',operation=None):
 args=['runuser','-u',user,'--',sys.executable,str(RUN/'client.py'),mode]
 if operation:args.append(operation)
 row=subprocess.run(args,capture_output=True,text=True,timeout=40)
 assert row.returncode==0,dict(rc=row.returncode,out=row.stdout,err=row.stderr)
 return json.loads(row.stdout)

def state(case):return {part:f.files(case/part) for part in ('catalog','inventory','ledger')}

def polkits(case):return [row for row in json.loads((case/'audit.json').read_text()) if row['event']=='polkit']

PATHS=[Path('/etc')/name for name in ('passwd','group','gshadow','shadow','passwd-','group-','gshadow-','shadow-')]
original={str(path):dict(data=path.read_bytes(),uid=path.stat().st_uid,gid=path.stat().st_gid,mode=path.stat().st_mode&0o777) if path.exists() else None for path in PATHS}
def hashes():return {str(path):hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None for path in PATHS}
def members(user):return sorted(g.gr_name for g in grp.getgrall() if user in g.gr_mem)
def peer():return dict(identity=f.identify(1000),profile=pwd.getpwnam('installeduser').pw_gecos,groups=members('installeduser'))
identity=f.identify(1002);peer_before=peer();initial_hashes=hashes()
assert 'wheel' not in members('ordinaryuser')
for entry in Path('/proc').iterdir():
 if entry.name.isdigit():
  try:uids=(entry/'status').read_text().split('Uid:')[1].splitlines()[0].split()
  except (FileNotFoundError,IndexError,ProcessLookupError):continue
  assert '1002' not in uids,'target has running processes'
backup=BASE/'account-backup';backup.mkdir(mode=0o700)
for path,row in original.items():
 if row is not None:
  saved=backup/Path(path).name;saved.write_bytes(row['data']);saved.chmod(0o600)
before=f.system_state();config_before=configs();processes=[];cases=[];passed=False;error=None
try:
 RUN.mkdir(mode=0o755);f.DATA.mkdir(mode=0o700)
 shutil.copyfile(BASE/'client.py',RUN/'client.py');(RUN/'client.py').chmod(0o644)
 CONF.write_text('<busconfig><policy user="root"><allow own="org.lyraos.ParentalFixture1"/></policy><policy context="default"><allow send_destination="org.lyraos.ParentalFixture1"/></policy></busconfig>\n')
 defaults=lambda rule:'<defaults><allow_any>'+rule+'</allow_any><allow_inactive>'+rule+'</allow_inactive><allow_active>'+rule+'</allow_active></defaults>'
 POLICY.write_text('<?xml version="1.0"?><policyconfig>'+''.join('<action id="org.lyraos.parental.fixture.'+name+'"><description>Disposable parental fixture</description><message>Disposable fixture authentication</message>'+defaults('auth_self' if name=='challenge' else 'no')+'</action>' for name in ('allow','deny','challenge'))+'</policyconfig>\n')
 RULE.write_text('polkit.addRule(function(action, subject) { if (subject.user === "installeduser" && action.id === "org.lyraos.parental.fixture.allow") return polkit.Result.YES; if (action.id === "org.lyraos.parental.fixture.deny") return polkit.Result.NO; });\n')
 for path in (CONF,POLICY,RULE):path.chmod(0o644)
 reload();wait_actions(True)
 for mode in ('profile','consumed','noop-grant','remove','noop-remove','payload-change','deny','cancel','revoke','catalog-change','barrier','replay','unauthorized','invalid','own'):
  case=f.DATA/mode;p=service(mode,case);initial=state(case);accounts_before=hashes()
  response=client(mode,user='ordinaryuser' if mode=='unauthorized' else 'installeduser')
  events=json.loads((case/'audit.json').read_text());checks=polkits(case)
  effects=[row for row in events if row['event'] in ('unix','noop')]
  entry=dict(case=mode,response=response,events=events,before=initial,after=state(case),accounts_before=accounts_before,accounts_after=hashes(),identity_preserved=f.identify(1002)==identity,peer_preserved=peer()==peer_before)
  cases.append(entry)
  assert entry['identity_preserved'] and entry['peer_preserved']
  assert response['uid']==(1002 if mode=='unauthorized' else 1000)
  assert all(event['uid']==response['uid'] for event in events if 'uid' in event)
  assert all(event['sender']==response['sender'] for event in events if 'sender' in event) if mode!='replay' else True
  assert all(row['locks_free']==['catalog.lock','.inventory-1002.lock','.gate-1002.lock'] for row in checks)
  assert all(row['locks_held']==['catalog.lock','.inventory-1002.lock','.gate-1002.lock'] for row in effects)
  if mode in ('profile','consumed','noop-grant','remove','noop-remove','payload-change'):
   assert response['result']=='OrdinaryMutationDispatched' and len(checks)==len(effects)==1
   assert checks[0]['returncode']==0
   assert initial==state(case),'administration wrote lifecycle metadata'
   if mode in ('noop-grant','noop-remove'):
    assert effects[0]['event']=='noop' and accounts_before==hashes()
   else:assert effects[0]['event']=='unix' and effects[0]['returncode']==0
   if mode=='profile':
    assert pwd.getpwnam('ordinaryuser').pw_gecos=='Lyra fixture $(literal)' and members('ordinaryuser')==['users']
   if mode in ('consumed','noop-grant','payload-change'):assert members('ordinaryuser')==['users','wheel']
   if mode in ('remove','noop-remove'):assert members('ordinaryuser')==['users']
   if mode=='consumed':assert response['repeat_error'].endswith('.Denied') and len(checks)==1
  elif mode=='own':
   assert response['result']=='OrdinaryEligible' and not checks and not effects
   assert initial==state(case) and accounts_before==hashes()
  else:
   expected='InvalidParameters' if mode=='invalid' else 'Conflict' if mode=='catalog-change' else 'Blocked' if mode=='barrier' else 'Denied'
   assert response['error'].endswith('.'+expected),response
   assert not effects and accounts_before==hashes()
   if mode not in ('catalog-change','barrier'):assert initial==state(case)
   if mode in ('replay','unauthorized','invalid'):assert not checks
   else:
    assert len(checks)==1
    if mode=='cancel':assert len(response['agent_calls'])==1 and checks[0]['returncode']!=0
    if mode=='deny':assert checks[0]['returncode']!=0
    if mode in ('revoke','catalog-change','barrier'):assert checks[0]['returncode']==0
  assert Path('/etc/shadow').read_bytes()==original['/etc/shadow']['data']
  assert [line for line in Path('/etc/passwd').read_bytes().splitlines() if not line.startswith(b'ordinaryuser:')]==[line for line in original['/etc/passwd']['data'].splitlines() if not line.startswith(b'ordinaryuser:')]
  stop(p)
 passed=True
except Exception as exc:
 error=repr(exc)
finally:
 for process in processes:
  if process.poll() is None:stop(process)
 for path in (CONF,POLICY,RULE):path.unlink(missing_ok=True)
 reload();wait_actions(False)
 if RUN.exists():shutil.rmtree(RUN)
 if f.DATA.exists():shutil.rmtree(f.DATA)
 f.guard()
 for path,row in original.items():
  file=Path(path)
  if row is None:file.unlink(missing_ok=True)
  elif not file.exists() or file.read_bytes()!=row['data']:
   file.write_bytes(row['data']);os.chown(file,row['uid'],row['gid']);file.chmod(row['mode'])
   fd=os.open(file,os.O_RDONLY);os.fsync(fd);os.close(fd)
 fd=os.open('/etc',os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
 shutil.rmtree(backup)
 after=f.system_state();config_after=configs()
 restored=hashes()==initial_hashes and before==after
 cleanup=not any(p.exists() for p in (RUN,CONF,POLICY,RULE,f.DATA,backup)) and all(p.poll() is not None for p in processes)
 receipt=dict(passed=passed,error=error,cases=cases,state_before=before,state_after=after,
   configs_before=config_before,configs_after=config_after,cleanup=cleanup,restored=restored,
   account_hashes_before=initial_hashes,account_hashes_after=hashes(),
   real_dbus=True,real_polkit=True,real_unix_effects=True,password_authentication=False,
   guardian_binding=False,production_integrated=False)
 (BASE/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert restored and config_before==config_after and cleanup
print(json.dumps(dict(passed=passed,cases=len(cases),error=error,cleanup=cleanup)))
sys.exit(0 if passed else 1)
