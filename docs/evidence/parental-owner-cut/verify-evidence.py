"""Check real VM cuts while publishing withdrawal ownership and unlinking proof."""
from pathlib import Path
import json,hashlib,re
P=Path(__file__).resolve().parent
load=lambda path:json.loads(path.read_text())
proof=load(P/'provenance.json')
for name,digest in proof['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in proof['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
cases=[(k,p) for k in ('marker','owner') for p in ('partial-write','temp-fsynced','renamed','directory-fsynced')]+[('proof','unlinked'),('proof','directory-synced')]
counts={'partial-write':(0,0,0),'temp-fsynced':(1,0,0),'renamed':(1,1,0),'directory-fsynced':(1,1,1)}
boots=[]
for kind,point in cases:
 C=P/(kind+'-'+point);s=load(C/'preboot-state.json');r=load(C/'result.json')
 assert s['kind']==kind and s['point']==point and r['passed'] is True and r['error'] is None and r['cleanup_rc']==0
 assert len(s['checks'])==6 and len(r['checks'])==8 and all(x['passed'] is True for x in s['checks']+r['checks'])
 assert s['old_boot']==r['old_boot'] and r['new_boot']!=r['old_boot'];boots.extend([r['old_boot'],r['new_boot']])
 for name,digest in s['source_sha256'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest
 rows={x['name']:x for x in r['checks']};assert rows['installed-admission-sources-survive-cut']['installed_files']==s['installed_files']
 guard=json.loads(load(C/'precut-guard-response.json')['stdout']);ready=guard['ready']
 assert guard['guard'] and guard['worker_state']=='T' and guard['boot']==s['old_boot'] and len(guard['helper_pids'])==2
 assert guard['properties']['MainPID'] in guard['helper_pids'] and int(guard['properties']['MainPID'])>0 and guard['properties']['ActiveState']=='active' and guard['properties']['Job'] in ('','0')
 assert ready['kind']==kind and ready['point']==ready['stage']==point and ready['authorization_calls']==1
 assert ready['writer_sha256']==s['metadata']['source_sha256']['barrier-writer.py']==hashlib.sha256((P.parent/'parental-registry-barrier/writer.py').read_bytes()).hexdigest()
 n=ready['counts']
 if kind!='proof':
  assert n['writes']>=1 and n['unlinks']==0 and (n['file_fsync'],n['renames'],n['directory_fsync'])==counts[point]
  temps={name:row for name,row in ready['files'].items() if name.startswith('.'+ready['name']+'.') and name.endswith('.tmp')}
  if not n['renames']:
   assert ready['canonical'] is None and len(temps)==1
   size=next(iter(temps.values()))['size'];assert size==(ready['payload_size']//2 if point=='partial-write' else ready['payload_size'])
  else:
   assert ready['canonical']['phase']=='intent' and ready['canonical']['operation']==s['operation'] and not temps
 else:
  assert n==dict(writes=0,file_fsync=0,renames=0,directory_fsync=0 if point=='unlinked' else 1,unlinks=1) and ready['canonical'] is None
 state=rows['interrupted-owner-state-is-whole-and-unacknowledged-before-marker'];assert state['kind']==kind and state['point']==point and state['quiescence_claimed'] is False
 blocked=state['blocked'];marker=state['marker'];owned=state['owned'];journal=state['journal'];files=state['files']
 assert blocked==(marker is not None) and rows['pam-attempts-do-not-promote-temporary-or-recreate-proof']['files']==files
 assert files['1000']['sha256']==s['peer_proof_sha256']
 if kind in ('marker','owner'):
  canonical=marker if kind=='marker' else owned
  if point in ('partial-write','temp-fsynced'):assert canonical is None
  if point=='directory-fsynced':assert canonical is not None
  if canonical is not None:assert canonical==ready['canonical'] and canonical['phase']=='intent' and canonical['revision']==1
  assert journal is None and state['proof_present'] is True and files['1002']['sha256']==s['original_target_proof_sha256']
  if kind=='marker':assert owned is None
  else:
   assert marker is not None and marker['phase']=='intent' and marker['operation']==s['operation']
   if owned is not None:assert owned==marker
 else:
  assert blocked and owned['phase']=='legacy-blocked' and owned['revision']==2
  assert marker==journal and marker['phase']=='blocked' and marker['revision']==1 and marker['operation']==owned['operation']==s['operation']
  for name in ('.deny-1002','.operation-1002.json','.withdrawal-1002.json'):assert files[name]==ready['files'][name]
  if point=='directory-synced':assert state['proof_present'] is False
  if state['proof_present']:assert files['1002']['sha256']==s['original_target_proof_sha256']
 assert rows['inspection-is-read-only']['outcome']==(dict(result='BlockedRecoveryRequired',code=None) if blocked else dict(result=None,code='RecoveryRequired'))
 assert rows['different-operation-refused-before-authorization']['outcome']['code']==('Conflict' if blocked else 'RecoveryRequired')
 denial=rows['fresh-denial-or-missing-marker-preserves-all-state'];assert denial['outcome']['code']==('Denied' if blocked else 'RecoveryRequired') and len(denial['authorization_calls'])==(1 if blocked else 0)
 if blocked:
  target=rows['durable-marker-denies-target-pam-even-if-proof-exists'];assert target['unit']['MainPID']=='0' and target['unit']['ExecMainStatus']=='224' and 'Experimental withdrawal admission rejected session' in target['journal']
 else:
  target=rows['uncommitted-withdrawal-preserves-original-admission'];assert int(target['unit']['MainPID'])>0 and target['withdrawal_acknowledged'] is False and target['context'].startswith('unconfined_u:unconfined_r:unconfined_t:')
 assert int(rows['peer-proof-preserved-and-new-admission-succeeds']['unit']['MainPID'])>0
 for name in ('initial-guard-response.json','preboot-response.json','precut-guard-response.json','new-boot-response.json','postboot-response.json','extra-restoration.json','poweroff-response.json'):assert load(C/name)['rc']==0
 assert json.loads(load(C/'postboot-response.json')['stdout'].splitlines()[-1])==dict(passed=True,checks=8,cleanup_rc=0)
 assert json.loads(load(C/'new-boot-response.json')['stdout'])==dict(guard=True,old_boot=s['old_boot'],new_boot=r['new_boot'])
 assert json.loads(load(C/'extra-restoration.json')['stdout'])==dict(passed=True)
 readers=load(C/'restoration-executions.json');assert {x['file'] for x in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
 for x in readers:assert x['response']['rc']==0 and json.loads(x['response']['stdout'])['passed'] is True
 cut=load(C/'cut.json');off=load(C/'vm-off.json');assert cut['signal']=='SIGKILL' and cut['pidfd_pinned'] is True and cut['guest_shutdown_requested'] is False
 assert 'file='+off['same_disk']+',format=qcow2,if=none,id=root' in cut['command'] and off['cut_qemu_returncode']==-9 and off['qemu_returncode']==0 and off['vm_off'] is True
 for key in ('full_account_protection','global_coverage_qualified','production_daemon_qualified','physical_power_loss_tested','producer_quiescence_qualified'):assert r[key] is False
 assert load(C/'disk.json')['full-backing-filename']=='/tmp/lyra-parental-identity-20260928/system.raw'
assert len(set(boots))==20
suite=(P/'python-suite.txt').read_text();assert re.search(r'Ran 744 tests in ',suite) and '\nOK\n' in suite
print('PASS: ten real marker/owner/proof VM cuts; 744 tests/140 VM controls/40 restoration readers; all VMs OFF. Before marker persistence withdrawal is unacknowledged; after it PAM remains denied. Production and physical power loss remain unqualified.')
