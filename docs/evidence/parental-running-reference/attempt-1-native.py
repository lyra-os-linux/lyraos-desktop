"""Isolated real process/configuration faults; reserved fixture only."""
from support import *
from running import capture as pin_process
from linux import Linux
import signal,time,select
BASE=Path('/root/running-reference-test')
UNIT=Path('/usr/lib/systemd/system/lyra-parental-running-probe.service')
BINARY=Path('/usr/libexec/lyra-parental-running-probe')
assert not UNIT.exists() and not UNIT.is_symlink() and not BINARY.exists() and not BINARY.is_symlink()
text='[Unit]\nDescription=Reserved parental running-reference VM probe\n[Service]\nType=exec\nUser=ordinaryuser\nExecStart='+str(BINARY)+'\n'
checks=[];passed=False;error=None;cleanup=False
account_paths=('/etc/passwd','/etc/group','/etc/pam.d/systemd-user')
accounts={p:fingerprint(p) for p in account_paths}
broker=run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()
meta=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),broker_pid=broker,source_sha256={n:hashlib.sha256((BASE/n).read_bytes()).hexdigest() for n in ('native.py','support.py','running.py','linux.py','probe.c','reference.py','namespace.py','catalog.py','coordinator.py')})
def record(name,**fields):checks.append(dict(name=name,passed=True,**fields));print(json.dumps(checks[-1]),flush=True)
def expect(codes,fn):
 try:fn()
 except GateError as e:
  assert e.code in codes,(e.code,codes);return e.code
 else:raise AssertionError('missing rejection')
def runtime(unit):
 output=json.loads(run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','GetUnit','s',unit]));assert output['type']=='o' and len(output['data'])==1
 return {n:json.loads(run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',output['data'][0],'org.freedesktop.systemd1.Service',n])) for n in ('MainPID','ControlGroup')}
backend=Linux(runtime)
def recapture(ref):return check(ref,properties,user,group,fingerprint)
def fresh():return capture(UNIT.name,properties,user,group,fingerprint)
def wait(fn):
 end=time.monotonic()+8
 while time.monotonic()<end:
  if fn():return
  time.sleep(.05)
 raise AssertionError('bounded observation timeout')
try:
 run(['cc','-Wall','-Wextra','-Werror','-O2','-o',str(BASE/'probe'),str(BASE/'probe.c')])
 BINARY.write_bytes((BASE/'probe').read_bytes());BINARY.chmod(0o755)
 UNIT.write_text(text);UNIT.chmod(0o644);run(['systemctl','daemon-reload'])
 ref=fresh()
 def cold():
  with pin_process(ref,backend,recapture):pass
 code=expect(('UnverifiedRuntime',),cold)
 record('inactive-unit-has-no-running-reference',code=code)
 run(['systemctl','start',UNIT.name])
 with pin_process(ref,backend,recapture) as pinned:
  initial=pinned.check();record('actual-main-process-pinned-with-configured-credentials',configuration=asdict(ref.configuration),observation=asdict(initial),reference=asdict(ref))
  UNIT.write_text(text+'# real source change during pinned observation\n')
  code=expect(('UnverifiedLoadedUnit','Conflict'),pinned.check)
  record('real-unit-source-change-invalidates-running-reference',code=code)
  UNIT.write_text(text);run(['systemctl','daemon-reload'])
  code=expect(('Conflict',),pinned.check)
  record('restored-unit-bytes-do-not-revive-old-source-reference',code=code)
 ref=fresh()
 with pin_process(ref,backend,recapture) as pinned:
  initial=pinned.check();record('fresh-source-reference-bound-to-same-original-process',observation=asdict(initial))
  signal.pidfd_send_signal(pinned._pin.descriptor,signal.SIGUSR1)
  wait(lambda:Path('/proc',str(initial.pid),'exe').resolve()==Path('/usr/bin/sleep'))
  changed=backend.read(pinned._pin)
  assert changed.pid==initial.pid and changed.start_ticks==initial.start_ticks and not backend.exited(pinned._pin)
  assert runtime(UNIT.name)['MainPID']['data']==initial.pid
  code=expect(('UnsupportedRuntime',),pinned.check)
  record('real-exec-with-same-pid-start-and-live-pidfd-refused',code=code,before=asdict(initial),after=asdict(changed))
  # Root-selected cleanup of this reserved service; not the product revocation API.
  run(['systemctl','stop',UNIT.name]);wait(lambda:backend.exited(pinned._pin))
  code=expect(('Conflict',),pinned.check)
  record('upstream-fixture-stop-observed-on-old-pidfd',code=code)
 run(['systemctl','start',UNIT.name])
 with pin_process(ref,backend,recapture) as replacement:
  row=replacement.check();assert row.pid!=initial.pid
  record('new-main-process-requires-new-pin',observation=asdict(row),previous_pid=initial.pid)
 assert accounts=={p:fingerprint(p) for p in accounts}
 assert run(['systemctl','show','dbus.service','-p','MainPID','--value']).strip()==broker
 record('account-pam-files-and-shared-broker-preserved',broker_pid=broker)
 passed=True
except BaseException as e:error=repr(e);raise
finally:
 # Only exact root-reserved paths from this fixture are removed.
 stop=subprocess.run(['systemctl','stop',UNIT.name],capture_output=True,text=True,timeout=30)
 UNIT.unlink(missing_ok=True);BINARY.unlink(missing_ok=True)
 reload=subprocess.run(['systemctl','daemon-reload'],capture_output=True,text=True,timeout=30)
 cleanup=stop.returncode==0 and reload.returncode==0 and not UNIT.exists() and not BINARY.exists()
 row=dict(passed=passed and cleanup,error=error,checks=checks,metadata=meta,original_accounts=accounts,cleanup=dict(passed=cleanup,stop_rc=stop.returncode,reload_rc=reload.returncode),full_account_protection=False,global_coverage_qualified=False,real_activation_or_revocation_adapter_qualified=False,shared_privileged_services_qualified=False)
 (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps(dict(passed=row['passed'],checks=len(checks),cleanup=cleanup)));assert cleanup
