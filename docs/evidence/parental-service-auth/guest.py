"""Install/remove narrow fixture policies only in a guarded disposable VM."""
import hashlib,json,os,shutil,subprocess,sys,time
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
 for mode in ('allow','deny','cancel','revoke','catalog-change','replay','unauthorized','own'):
  case=f.DATA/mode;p=service(mode,case);initial=state(case)
  response=client(mode if mode in ('cancel','replay','own') else 'execute',user='ordinaryuser' if mode=='unauthorized' else 'installeduser')
  events=json.loads((case/'audit.json').read_text());checks=polkits(case)
  entry=dict(case=mode,response=response,events=events,before=initial,after=state(case))
  cases.append(entry)
  assert response['uid']==(1002 if mode=='unauthorized' else 1000)
  assert all(event['uid']==response['uid'] for event in events)
  assert all(event['sender']==response['sender'] for event in events) if mode!='replay' else True
  if mode=='allow':
   assert response['result']=='AdmissionWithdrawnNoQuiescence'
   assert len(checks)==1 and checks[0]['returncode']==0 and len(checks[0]['locks_free'])==3
   assert not (case/'ledger/1002').exists()
   for part in ('catalog','inventory'):assert initial[part]==state(case)[part]
   for name,data in initial['ledger'].items():
    if '1000' in name:assert data==state(case)['ledger'][name]
   before_retry=state(case);stop(p);(case/'ready').unlink();p=service('allow',case)
   retry=client('resume',operation=response['plan']);entry['retry']=retry
   assert retry['result']=='AdmissionWithdrawnNoQuiescence'
   assert state(case)==before_retry
   assert len(polkits(case))==1 and polkits(case)[0]['returncode']==0
  elif mode=='own':
   assert response['result']=='OrdinaryEligible' and not checks
   assert initial==state(case)
  else:
   assert response['error'].endswith('.AuthorizationFailure' if mode in ('revoke','catalog-change') else '.Denied'),response
   assert initial['ledger']==state(case)['ledger']
   if mode!='catalog-change':assert initial==state(case)
   if mode in ('replay','unauthorized'):assert not checks
   else:
    assert len(checks)==1
    if mode=='cancel':assert len(response['agent_calls'])==1 and checks[0]['returncode']!=0
    if mode=='deny':assert checks[0]['returncode']!=0
    if mode in ('revoke','catalog-change'):assert checks[0]['returncode']==0
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
 after=f.system_state();config_after=configs()
 cleanup=not any(p.exists() for p in (RUN,CONF,POLICY,RULE,f.DATA)) and all(p.poll() is not None for p in processes)
 receipt=dict(passed=passed,error=error,cases=cases,state_before=before,state_after=after,
   configs_before=config_before,configs_after=config_after,cleanup=cleanup,
   real_dbus=True,real_polkit=True,password_authentication=False,guardian_binding=False,
   production_integrated=False)
 (BASE/'result.json').write_text(json.dumps(receipt,indent=2)+'\n')
 assert before==after and config_before==config_after and cleanup
print(json.dumps(dict(passed=passed,cases=len(cases),error=error,cleanup=cleanup)))
sys.exit(0 if passed else 1)
