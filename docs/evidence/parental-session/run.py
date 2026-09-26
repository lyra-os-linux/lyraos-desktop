"""Host controller for the single marked disposable VM; never injects host keys."""
import ast,json,pathlib,subprocess,sys,time
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
# The minimal VM initramfs can recreate /run/udev with generic labels on boot.
# Fail before modifying the fixture: repair its upstream labels outside the test.
cmd('matchpathcon','-V','/run/udev','/run/udev/data')
# All transferred files are test harness or fixed native probes under /root.
for source,target in [('localsearch.cil','localsearch.cil'),('nautilus-portal.c','nautilus-portal.c'),('audio-probe.c','audio-probe.c'),('session-data.cil','session-data.cil'),('fusermount.cil','fusermount.cil'),('portal-probe.c','portal-probe.c'),('trusted-wireplumber.c','trusted-wireplumber.c'),('wireplumber.cil','wireplumber.cil'),('exercise.py','xwayland-exercise.py'),('session.py','restricted-xwayland-session.py'),('launch-probe.c','launch-probe.c'),('input-probe.c','input-probe.c'),('input-window.c','input-window.c'),('fixture_recovery.py','fixture_recovery.py'),('verify-final.py','input-verify-final.py')]:
 subprocess.run(['python3',str(CONTROL),'transfer',str(OUT/source),'/root/'+target],check=True,capture_output=True)
cmd('python3','-c',"from pathlib import Path; Path('/root/input-phase.json').write_text('{}')")
cmd('python3','-c',"from pathlib import Path; [Path('/root/'+n).unlink(missing_ok=True) for n in ['trusted-shell-session.json','trusted-shell-audit.json','trusted-shell-progress.json','trusted-shell-config-faults.json','trusted-shell-stderr.log']]")
unit='lyra-parental-'+tag
cmd('systemd-run','--unit='+unit,'-p','Environment=LYRA_PARENTAL_DIAGNOSTIC='+('1' if tag.startswith('diag') else '0'),'-p','RuntimeMaxSec=300','-p','TimeoutStopSec=180','-p','StandardOutput=append:/root/xwayland-'+tag+'-result.json','-p','StandardError=append:/root/xwayland-'+tag+'-stderr.log','-p','ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py','/usr/bin/python3','/root/xwayland-exercise.py')
sent=[];deadline=time.monotonic()+490
while time.monotonic()<deadline:
 phase=json.loads(cmd('cat','/root/input-phase.json')).get('phase')
 if phase in ['approved','blocked','typing','preparechooser','chooser','chooserselect'] and phase not in sent:
  if phase=='typing':
   result=vm('key','esc','esc')
   print(json.dumps(dict(phase=phase,focus_keys=['esc','esc'],result=result)),flush=True)
   time.sleep(.5)
  def click(x,y):
   events=[{'type':'abs','data':{'axis':'x','value':round(x*32767/1280)}},
           {'type':'abs','data':{'axis':'y','value':round(y*32767/800)}},
           {'type':'btn','data':{'down':True,'button':'left'}}]
   result=ast.literal_eval(vm('qmp','input-send-event',json.dumps({'events':events})))
   assert 'return' in result,result
   time.sleep(.15)
   result=ast.literal_eval(vm('qmp','input-send-event',json.dumps({'events':[{'type':'btn','data':{'down':False,'button':'left'}}]})))
   assert 'return' in result,result
  if phase=='chooser':
   time.sleep(2)
   vm('shot',tag+'-chooser')

  key='esc' if phase in ['chooser','preparechooser'] else ('a' if phase=='typing' else 'meta_l+shift+f9')
  if phase=='chooser':
   key='cancel file chooser'
   click(1062,164)
   time.sleep(1)
   vm('shot',tag+'-after-cancel')
   result='QMP close-button click'
  elif phase=='chooserselect':
   click(640,164)
   time.sleep(.3)
   key='select disposable chooser.txt'
   keys=['ctrl+l']+[{'/':'slash','.':'dot'}.get(c,c) for c in '/home/parentaltest/chooser.txt']+['ret']
   vm('key',*keys)
   time.sleep(.5)
   click(1014,656)
   time.sleep(1)
   vm('shot',tag+'-after-select')
   result='QMP '+str(len(keys))+' fixed keys'
  else:result=vm('key',key)
  sent.append(phase)
  print(json.dumps(dict(phase=phase,key=key,result=result)),flush=True)
  (OUT/(tag+'-keys.json')).write_text(json.dumps(sent))
 state=cmd('systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','Result')
 if 'ActiveState=inactive\n' in state or 'ActiveState=failed\n' in state:
  print(state,flush=True);break
 time.sleep(2)
else:raise RuntimeError('VM experiment did not complete within deadline')
subprocess.run(['python3',str(OUT/'collect.py'),tag,str(ROOT)],check=True)
