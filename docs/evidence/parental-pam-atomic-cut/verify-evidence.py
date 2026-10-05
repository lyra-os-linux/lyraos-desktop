"""Verify real syscall-boundary VM cuts and refusal of obsolete authority."""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda p:json.loads(p.read_text())
proof=load(P/'provenance.json')
for name,digest in proof['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in proof['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
expected_counts={'partial-write':(0,0,0),'temp-fsynced':(1,0,0),'renamed':(1,1,0),'directory-fsynced':(1,1,1)}
boots=[]
for point,(file_sync,renames,dir_sync) in expected_counts.items():
 C=P/point;s=load(C/'preboot-state.json');r=load(C/'result.json')
 assert s['point']==point and r['passed'] is True and r['cleanup_rc']==0 and r['error'] is None
 assert len(s['checks'])==13 and len(r['checks'])==9 and all(x['passed'] is True for x in s['checks']+r['checks'])
 assert s['old_boot']==r['old_boot'] and r['new_boot']!=r['old_boot'];boots.extend([r['old_boot'],r['new_boot']])
 for name,digest in s['source_sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
 rows={x['name']:x for x in r['checks']}
 installed=rows['postcut-installed-pam-and-unit-sources-intact']['installed_files'];assert installed==s['installed_files']
 assert next(x for x in s['checks'] if x['name']=='fixture-installation-durable-before-withdrawal')['installed_files']==installed
 guard=json.loads(load(C/'precut-guard-response.json')['stdout']);ready=guard['ready']
 assert guard['guard'] and guard['marker_present'] and guard['helper_pids'] and guard['worker_state']=='T' and guard['boot']==s['old_boot']
 assert guard['properties']['MainPID']=='0' and guard['properties']['ActiveState']=='deactivating' and int(guard['properties']['Job'])>0
 assert ready['point']==ready['stage']==point and ready['request_entries']==ready['request_returns']==1
 counts=ready['counts'];assert counts['writes']>=1 and (counts['file_fsync'],counts['renames'],counts['directory_fsync'])==(file_sync,renames,dir_sync)
 assert ready['writer_sha256']==s['metadata']['source_sha256']['barrier-writer.py']==hashlib.sha256((P.parent/'parental-registry-barrier/writer.py').read_bytes()).hexdigest()
 pre=ready['canonical'];assert pre['boot_id']==s['old_boot'] and pre['owner']['operation']==s['operation']
 if not renames:
  assert pre['phase']=='intent' and pre['job'] is None and len(ready['temps'])==1
  size=ready['temps'][0]['size'];assert size==(ready['payload_size']//2 if point=='partial-write' else ready['payload_size'])
 else:assert pre['phase']=='accepted' and pre['job']==ready['reply']['data'][0] and ready['temps']==[]
 post=rows['interrupted-atomic-write-retains-whole-old-or-new-canonical-journal']['canonical']
 allowed=('intent',) if not renames else ('accepted',) if dir_sync else ('intent','accepted')
 assert post['phase'] in allowed and post['boot_id']==s['old_boot'] and post['owner']==pre['owner']
 assert post['revision']==(1 if post['phase']=='intent' else 2)
 assert post['job']==(None if post['phase']=='intent' else ready['reply']['data'][0])
 negative=rows['real-new-boot-keeps-old-accepted-effect-and-negative-artifacts']
 assert negative['artifacts']==s['artifacts'] and negative['protected_proof_missing'] is True
 assert negative['unit']['LoadState']=='masked' and negative['unit']['MainPID']=='0' and s['artifacts']['mask']['link']=='/dev/null'
 consumers=[]
 for mode in ('deny','allow'):
  c=rows['cross-boot-'+mode+'-refused-before-authorization-without-job-reuse']['consumer'];consumers.append(c)
  assert c['boot']==r['new_boot'] and c['outcome']=='blocked' and c['code']=='RecoveryRequired'
  assert c['authorization_calls']==c['ipc_requests']==c['inherited_pidfds']==[] and c['result'] is None and c['empty'] is True
  assert c['properties']['MainPID']['data']==0 and c['properties']['Job']['data']==[0,'/'] and c['properties']['InvocationID']['data']==[]
 assert consumers[0]['pid']!=consumers[1]['pid']
 for name in ('withdrawn-pam-admission-still-rejected-after-real-reboot','withdrawn-user-manager-still-rejected-in-new-boot'):
  assert rows[name]['unit']['MainPID']=='0' and rows[name]['unit']['ExecMainStatus']=='224'
 assert rows['peer-proof-preserved-and-fresh-peer-admission-succeeds']['old_peer_pid_reused_as_authority'] is False
 for key in ('full_account_protection','global_coverage_qualified','production_daemon_qualified','cross_boot_recovery_authorized','physical_power_loss_tested'):assert r[key] is False
 assert r['abrupt_vm_stop_tested'] is True
 readers=load(C/'restoration-executions.json');assert {x['file'] for x in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
 for x in readers:assert x['response']['rc']==0 and json.loads(x['response']['stdout'])['passed'] is True
 for name in ('initial-guard-response.json','preboot-response.json','precut-guard-response.json','new-boot-response.json','postboot-response.json','extra-restoration.json','poweroff-response.json'):assert load(C/name)['rc']==0
 assert json.loads(load(C/'extra-restoration.json')['stdout'])==dict(passed=True)
 assert json.loads(load(C/'postboot-response.json')['stdout'].splitlines()[-1])==dict(passed=True,checks=9,cleanup_rc=0)
 assert json.loads(load(C/'new-boot-response.json')['stdout'])==dict(guard=True,old_boot=s['old_boot'],new_boot=r['new_boot'])
 cut=load(C/'cut.json');off=load(C/'vm-off.json');assert cut['signal']=='SIGKILL' and cut['pidfd_pinned'] is True and cut['guest_shutdown_requested'] is False
 assert 'file='+off['same_disk']+',format=qcow2,if=none,id=root' in cut['command']
 assert off['cut_qemu_returncode']==-9 and off['qemu_returncode']==0 and off['vm_off'] is True
 assert load(C/'disk.json')['full-backing-filename']=='/tmp/lyra-parental-identity-20260928/system.raw'
assert len(set(boots))==8
suite=(P/'python-suite.txt').read_text();assert re.search(r'Ran 744 tests in ',suite) and '\nOK\n' in suite
print('PASS: four actual accepted-journal syscall cuts; 744 tests/88 VM controls/16 restoration readers; all VMs OFF. Intent/origin cuts, physical power loss and production remain unqualified.')
