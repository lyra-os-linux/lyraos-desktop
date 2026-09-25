"""Host controller for the single marked disposable VM; never injects host keys."""
import json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(sys.argv[2]).resolve() if len(sys.argv)>2 else pathlib.Path(__file__).resolve().parents[3]
VM=ROOT/'analysis/2026-09-25/parental-gdm/vm.py'
CONTROL=VM.with_name('control.py')
OUT=pathlib.Path(__file__).resolve().parent
tag=sys.argv[1]
assert tag.isalnum()
def vm(*args):
 r=subprocess.run(['python3',str(VM),'virtualization',*args],capture_output=True,text=True,timeout=125)
 if r.returncode:raise RuntimeError(r.stdout+r.stderr)
 return r.stdout
def cmd(*args):return json.loads(vm('cmd',*args))['stdout']
assert 'lyra.parental-selinux-test=1' in cmd('cat','/proc/cmdline').split()
assert cmd('test','!','-e','/root/lyra-xwayland-recovery/active.json')==''
# All transferred files are test harness or fixed native probes under /root.
for source,target in [('exercise.py','xwayland-exercise.py'),('session.py','restricted-xwayland-session.py'),('launch-probe.c','launch-probe.c'),('input-probe.c','input-probe.c'),('input-window.c','input-window.c'),('fixture_recovery.py','fixture_recovery.py'),('verify-final.py','input-verify-final.py')]:
 subprocess.run(['python3',str(CONTROL),'transfer',str(OUT/source),'/root/'+target],check=True,capture_output=True)
cmd('python3','-c',"from pathlib import Path; Path('/root/input-phase.json').write_text('{}')")
cmd('python3','-c',"from pathlib import Path; [Path('/root/'+n).unlink(missing_ok=True) for n in ['trusted-shell-session.json','trusted-shell-audit.json','trusted-shell-progress.json','trusted-shell-config-faults.json','trusted-shell-stderr.log']]")
unit='lyra-parental-'+tag
cmd('systemd-run','--unit='+unit,'-p','RuntimeMaxSec=300','-p','TimeoutStopSec=180','-p','StandardOutput=append:/root/xwayland-'+tag+'-result.json','-p','StandardError=append:/root/xwayland-'+tag+'-stderr.log','-p','ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py','/usr/bin/python3','/root/xwayland-exercise.py')
sent=[];deadline=time.monotonic()+490
while time.monotonic()<deadline:
 phase=json.loads(cmd('cat','/root/input-phase.json')).get('phase')
 if phase in ['approved','blocked','typing'] and phase not in sent:
  if phase=='typing':
   result=vm('key','esc','esc')
   print(json.dumps(dict(phase=phase,focus_keys=['esc','esc'],result=result)),flush=True)
   time.sleep(.5)
  key='a' if phase=='typing' else 'meta_l+shift+f9'
  result=vm('key',key)
  sent.append(phase)
  print(json.dumps(dict(phase=phase,key=key,result=result)),flush=True)
  (OUT/(tag+'-keys.json')).write_text(json.dumps(sent))
 state=cmd('systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','Result')
 if 'ActiveState=inactive\n' in state or 'ActiveState=failed\n' in state:
  print(state,flush=True);break
 time.sleep(2)
else:raise RuntimeError('VM experiment did not complete within deadline')
subprocess.run(['python3',str(OUT/'collect.py'),tag,str(ROOT)],check=True)
