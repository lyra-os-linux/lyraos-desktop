"""Four isolated VM cuts at actual syscalls of the existing atomic writer."""
from pathlib import Path
import subprocess,json,time,os,signal,hashlib,sys
ROOT=Path('/home/rodrigo/Git/LyraOS');A=Path(__file__).resolve().parent
E=ROOT/'worktrees/desktop-parental-registry-lifetime/docs/evidence/parental-pam-early-cut'
BACK=Path('/tmp/lyra-parental-identity-20260928/system.raw')
FILES={'parental-pam-unit-stop':['pam.py'],'parental-pam-helper-recovery':['recovery.py'],'parental-cold-unit-stop':['cold.py'],'parental-pam-main-exit':['pam-close-hold.c'],'parental-pam-daemon-recovery':['restart.py','restarted-reader.py'],'parental-pam-early-cut':['prepare-early.py','early-worker.py','postboot.py','postboot-consumer.py']}
for kind,point in ((k,p) for k in ('origin','intent') for p in ('partial-write','temp-fsynced','renamed','directory-fsynced')):
 key=kind+'-'+point
 if (E/key/'vm-off.json').exists():
  print(key+': already qualified, skipped',flush=True);continue
 case=A/key;case.mkdir(exist_ok=False);out=E/key;out.mkdir(exist_ok=False)
 base=Path('/tmp/lyra-parental-pam-early-20261005')/key;base.mkdir(mode=0o700,parents=True,exist_ok=False)
 assert BACK.is_file()
 subprocess.run(['qemu-img','create','-f','qcow2','-F','raw','-b',str(BACK),str(base/'system.qcow2')],check=True,capture_output=True)
 info=json.loads(subprocess.check_output(['qemu-img','info','--output=json',str(base/'system.qcow2')],text=True));assert info['full-backing-filename']==str(BACK) and info['backing-filename-format']=='raw';(out/'disk.json').write_text(json.dumps(info,indent=2)+'\n')
 for name in ('vm.py','host.py'):(case/name).write_text((A/name).read_text().replace('/tmp/lyra-parental-pam-powercut-20261005',str(base)))
 def launch():return subprocess.Popen(['python3',str(case/'vm.py'),'virtualization','launch'],stdout=(case/'qemu-output.txt').open('ab'),stderr=subprocess.STDOUT)
 def guest(*args):
  p=subprocess.run(['python3',str(case/'vm.py'),'virtualization','cmd',*args],capture_output=True,text=True,timeout=920)
  if not p.stdout:raise RuntimeError(p.stderr)
  row=json.loads(p.stdout);return row
 def save(name,row):(out/name).write_text(json.dumps(row,indent=2)+'\n')
 def checked(name,*args):
  row=guest(*args);save(name,row);assert row['rc']==0,row;return row
 def wait_ready():
  deadline=time.monotonic()+60
  while True:
   try:
    row=guest('true')
    if row['rc']==0:return
   except (RuntimeError,OSError):pass
   assert time.monotonic()<deadline;time.sleep(.1)
 vm=launch();cut_vm=None
 try:
  wait_ready()
  checked('initial-guard-response.json','python3','-c',"from pathlib import Path;import os,json;assert os.geteuid()==0; c=Path('/proc/cmdline').read_text().split();assert 'lyra.parental-identity-test=1' in c and 'lyra.parental-selinux-test=1' in c;assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test';print(json.dumps(dict(guard=True)))")
  for directory,names in FILES.items():
   for name in names:subprocess.run(['python3',str(case/'host.py'),'push',str(E.parent/directory/name),'/root/unit-stop-jobs/'+name],check=True,capture_output=True)
  checked('preboot-response.json','python3','/root/unit-stop-jobs/prepare-early.py',point,kind)
  subprocess.run(['python3',str(case/'host.py'),'pull','/root/unit-stop-jobs/early-state.json',str(out/'preboot-state.json')],check=True)
  fd=os.pidfd_open(vm.pid)
  try:
   command=Path('/proc',str(vm.pid),'cmdline').read_bytes().split(b'\0');assert command[0].endswith(b'qemu-system-x86_64') and ('file='+str(base/'system.qcow2')+',format=qcow2,if=none,id=root').encode() in command
   checked('precut-guard-response.json','python3','-c',"""from pathlib import Path
import os,json,subprocess
assert os.geteuid()==0;cmd=Path('/proc/cmdline').read_text().split();assert 'lyra.parental-identity-test=1' in cmd and 'lyra.parental-selinux-test=1' in cmd
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
s=json.loads(Path('/root/unit-stop-jobs/early-state.json').read_text());r=json.loads(Path('/run/lyra-atomic-cut-ready.json').read_text());assert r['point']==s['point'] and r['kind']==s['kind'] and r['request_entries']==r['request_returns']==0
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['old_boot']
state=next(x.split()[1] for x in Path('/proc',str(r['pid']),'status').read_text().splitlines() if x.startswith('State:'));assert state=='T'
props=dict(x.split('=',1) for x in subprocess.check_output(['systemctl','show',s['unit'],'-p','ActiveState','-p','MainPID','-p','Job'],text=True).splitlines())
pids=Path('/sys/fs/cgroup/system.slice',s['unit'],'cgroup.procs').read_text().split();assert pids
if s['kind']=='origin':
 assert len(pids)==2 and int(props['MainPID'])>0 and props['MainPID'] in pids and props['ActiveState']=='active' and props['Job'] in ('','0')
 assert not Path('/run/lyra-pam-close-hold-test').exists()
else:
 assert len(pids)==1 and props['MainPID']=='0' and props['ActiveState']=='deactivating' and props['Job'] in ('','0')
 assert Path('/run/lyra-pam-close-hold-test').exists()
print(json.dumps(dict(guard=True,ready=r,boot=s['old_boot'],properties=props,helper_pids=pids,marker_present=Path('/run/lyra-pam-close-hold-test').exists(),worker_state=state)))
""")
   signal.pidfd_send_signal(fd,signal.SIGKILL)
   save('cut.json',dict(signal='SIGKILL',pidfd_pinned=True,qemu_pid=vm.pid,guest_shutdown_requested=False,command=[x.decode() for x in command if x],physical_power_loss_tested=False))
  finally:os.close(fd)
  cut_vm=vm.wait(timeout=15);assert cut_vm==-9
  print(key+': QEMU killed at actual writer boundary',flush=True)
  vm=launch();wait_ready()
  checked('new-boot-response.json','python3','-c',"from pathlib import Path;import os,json;assert os.geteuid()==0;c=Path('/proc/cmdline').read_text().split();assert 'lyra.parental-identity-test=1' in c and 'lyra.parental-selinux-test=1' in c;assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test';s=json.loads(Path('/root/unit-stop-jobs/early-state.json').read_text());b=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert b!=s['old_boot'];print(json.dumps(dict(guard=True,old_boot=s['old_boot'],new_boot=b)))")
  response=guest('python3','/root/unit-stop-jobs/postboot.py');save('postboot-response.json',response)
  subprocess.run(['python3',str(case/'host.py'),'pull','/root/unit-stop-jobs/early-result.json',str(out/'result.json')],check=True)
  assert response['rc']==0,response
  rows=[]
  for name in ('restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'):
   row=guest('python3','/root/unit-stop-jobs/'+name);rows.append(dict(file=name,response=row));assert row['rc']==0 and json.loads(row['stdout'])['passed'] is True
  save('restoration-executions.json',rows)
  checked('extra-restoration.json','python3','-c',"from pathlib import Path;import json,subprocess;assert not any(Path(p).exists() for p in ('/etc/pam.d/lyra-parental-unit-test','/run/lyra-pam-close-hold-test','/run/lyra-atomic-cut-ready.json','/var/lib/lyra-unit-stop-effects-test'));assert subprocess.check_output(['getenforce'],text=True).strip()=='Permissive';print(json.dumps(dict(passed=True)))")
  checked('poweroff-response.json','systemctl','poweroff');status=vm.wait(timeout=45);assert status==0
  save('vm-off.json',dict(cut_qemu_returncode=cut_vm,qemu_returncode=status,vm_off=True,same_disk=str(base/'system.qcow2')))
  print(key+': PASS; restoration confirmed and VM OFF',flush=True)
 finally:
  if vm.poll() is None:
   # On failure preserve overlay/evidence, terminate only the owned test process.
   fd=os.pidfd_open(vm.pid)
   try:signal.pidfd_send_signal(fd,signal.SIGKILL)
   finally:os.close(fd)
   vm.wait(timeout=15)
print('ALL EIGHT CASES PASS',flush=True)
