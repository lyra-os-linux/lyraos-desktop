"""Terminate only the pinned QEMU for the validated disposable test overlay."""
import json,os,signal,subprocess,time
from pathlib import Path
A=Path(__file__).resolve().parent
E=Path('/home/rodrigo/Git/LyraOS/worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-pam-powercut')
B=Path('/tmp/lyra-parental-pam-powercut-20261005')
def guest(*args):
 p=subprocess.run(['python3',str(A/'vm.py'),'virtualization','cmd',*args],capture_output=True,text=True,check=True)
 r=json.loads(p.stdout);assert r['rc']==0;return r
r=guest('python3','/root/unit-stop-jobs/prepare-powercut.py');(E/'preboot-response.json').write_text(json.dumps(r,indent=2)+'\n')
assert json.loads(r['stdout'].splitlines()[-1])['prepared'] is True
subprocess.run(['python3',str(A/'host.py'),'pull','/root/unit-stop-jobs/powercut-state.json',str(E/'preboot-state.json')],check=True)
pid=int((B/'virtualization/pid').read_text());fd=os.pidfd_open(pid)
try:
 cmd=Path('/proc',str(pid),'cmdline').read_bytes().split(b'\0');assert cmd[0].endswith(b'qemu-system-x86_64') and ('file='+str(B/'system.qcow2')+',format=qcow2,if=none,id=root').encode() in cmd
 assert b'lyra-virtualization-test-virtualization' in cmd
 response=guest('python3','-c',"""import os,json,subprocess
from pathlib import Path
assert os.geteuid()==0
cmdline=Path('/proc/cmdline').read_text().split()
assert 'lyra.parental-identity-test=1' in cmdline and 'lyra.parental-selinux-test=1' in cmdline
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
s=json.loads(Path('/root/unit-stop-jobs/powercut-state.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==s['old_boot']
unit=s['unit'];props=dict(line.split('=',1) for line in subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','-p','MainPID','-p','Job'],text=True).splitlines())
pids=Path('/sys/fs/cgroup/system.slice',unit,'cgroup.procs').read_text().split();assert pids
assert props['ActiveState']=='deactivating' and props['MainPID']=='0' and props['Job'] not in ('','0')
assert Path('/run/lyra-pam-close-hold-test').exists()
print(json.dumps(dict(guard=True,boot=boot,pending=s['pending'],properties=props,helper_pids=pids,marker_present=True)))
""")
 (E/'precut-guard-response.json').write_text(json.dumps(response,indent=2)+'\n')
 # Pinned process identity avoids signalling an unrelated process after PID reuse.
 before=time.time();signal.pidfd_send_signal(fd,signal.SIGKILL)
 (E/'cut.json').write_text(json.dumps(dict(qemu_pid=pid,signal='SIGKILL',sent_at=before,guest_shutdown_requested=False,pidfd_pinned=True,command=[x.decode() for x in cmd if x],physical_power_loss_tested=False),indent=2)+'\n')
finally:os.close(fd)
print('SIGKILL sent to verified pinned disposable QEMU; no guest shutdown')
