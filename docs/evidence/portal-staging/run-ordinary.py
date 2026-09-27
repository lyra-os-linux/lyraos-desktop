"""Host driver: keys and screenshots go only to the marked disposable QEMU guest."""
import json,pathlib,subprocess,sys,time
ROOT=pathlib.Path(sys.argv[1]).resolve()
OUT=pathlib.Path(__file__).resolve().parent
VM=ROOT/'analysis/2026-09-25/parental-gdm/vm.py';CONTROL=VM.with_name('control.py')
def vm(*args):
 p=subprocess.run(['python3',str(VM),'virtualization',*args],capture_output=True,text=True,timeout=90)
 assert p.returncode==0,p.stdout+p.stderr
 return p.stdout
def cmd(*args):return json.loads(vm('cmd',*args))['stdout']
assert 'lyra.parental-selinux-test=1' in cmd('cat','/proc/cmdline').split()
cmd('test','!','-e','/root/lyra-xwayland-recovery/active.json')
subprocess.run(['python3',str(CONTROL),'transfer',str(OUT/'ordinary.py'),'/root/portal-ordinary.py'],check=True)
cmd('python3','-c',"from pathlib import Path; Path('/root/input-phase.json').write_text('{}')")
tag=sys.argv[2] if len(sys.argv)>2 else 'ordinary1'
assert tag.isalnum()
unit='lyra-portal-'+tag
log='/var/log/lyra-parental-fixture/portal-'+tag
cmd('systemd-run','--unit='+unit,'-p','RuntimeMaxSec=240','-p','TimeoutStopSec=90','-p','StandardOutput=append:'+log+'.out','-p','StandardError=append:'+log+'.err','-p','ExecStopPost=/usr/bin/python3 /root/portal-ordinary.py recover','/usr/bin/python3','/root/portal-ordinary.py')
sent=[];deadline=time.monotonic()+350
while time.monotonic()<deadline:
 phase=json.loads(cmd('cat','/root/input-phase.json')).get('phase')
 if phase in ['shortcuts-cancel','shortcuts-bind','shortcuts-activate','shortcuts-released'] and phase not in sent:
  time.sleep(2);vm('shot','rpm-'+tag+'-'+phase)
  key={'shortcuts-cancel':'esc','shortcuts-bind':'alt+a','shortcuts-activate':'ctrl+shift+f8','shortcuts-released':'ctrl+shift+f8'}[phase]
  vm('key',key);sent.append(phase);print(phase,flush=True)
 state=cmd('systemctl','show',unit,'-p','ActiveState','-p','SubState','-p','Result')
 if 'ActiveState=inactive\n' in state or 'ActiveState=failed\n' in state:break
 time.sleep(1)
else:raise RuntimeError('Ordinary fixture deadline reached; inspect recovery')
(OUT/'ordinary-unit.json').write_text(json.dumps(dict(state=state,keys=sent),indent=2))
for source,target in [('/root/portal-ordinary.json','ordinary.json'),('/root/portal-ordinary-restored.json','ordinary-restored.json'),(log+'.err','ordinary-stderr.log'),(log+'.out','ordinary-stdout.log')]:
 subprocess.run(['python3',str(CONTROL),'pull',source,str(OUT/target)],check=True)
assert 'Result=success\n' in state,state
assert sent==['shortcuts-cancel','shortcuts-bind','shortcuts-activate','shortcuts-released'],sent
assert not (OUT/'ordinary-stderr.log').read_text()
print('Ordinary session PASS')
