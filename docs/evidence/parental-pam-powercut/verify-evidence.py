"""Check abrupt VM termination, unchanged negative authority and restoration."""
import hashlib,json,re
from pathlib import Path
P=Path(__file__).resolve().parent
load=lambda name:json.loads((P/name).read_text())
provenance=load('provenance.json')
for name,digest in provenance['artifacts'].items():assert hashlib.sha256((P/name).read_bytes()).hexdigest()==digest,name
for name,digest in provenance['dependencies'].items():assert hashlib.sha256((P.parent/name).read_bytes()).hexdigest()==digest,name
s=load('preboot-state.json');r=load('result.json')
assert r['passed'] is True and r['cleanup_rc']==0 and r['error'] is None
assert r['old_boot']==s['old_boot'] and r['old_boot']!=r['new_boot']
assert len(s['checks'])==15 and len(r['checks'])==8 and all(x['passed'] is True for x in s['checks']+r['checks'])
assert s['pending']['phase']=='accepted' and s['pending']['boot_id']==s['old_boot']
assert s['trace']['request_entries']==s['trace']['request_returns']==1 and s['trace']['crash_stage']=='acceptance-synced'
for name,digest in s['source_sha256'].items():
 path=P.parent/'parental-pam-crash-recovery'/name if name=='crash-worker.py' else P/name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
rows={x['name']:x for x in r['checks']}
first=rows['real-new-boot-keeps-old-accepted-effect-and-negative-artifacts']
assert first['artifacts']==s['artifacts'] and first['protected_proof_missing'] is True
assert first['unit']['MainPID']=='0' and first['unit']['LoadState']=='masked'
assert s['artifacts']['mask']['link']=='/dev/null'
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
readers=load('restoration-executions.json');assert {x['file'] for x in readers}=={'restore-check.py','restore-units.py','restore-ownership.py','restore-extra.py'}
for reader in readers:assert reader['response']['rc']==0 and json.loads(reader['response']['stdout'])['passed'] is True
extra=load('extra-restoration.json');assert extra['rc']==0
assert json.loads(extra['stdout'])==dict(passed=True,profile_removed=True,close_hold_removed=True,effects_removed=True,selinux='Permissive')
for name in ('preboot-response.json','new-boot-response.json','postboot-response.json','precut-guard-response.json','poweroff-response.json'):assert load(name)['rc']==0
assert json.loads(load('preboot-response.json')['stdout'].splitlines()[-1])['prepared'] is True
assert json.loads(load('postboot-response.json')['stdout'].splitlines()[-1])==dict(passed=True,checks=8,cleanup_rc=0)
assert json.loads(load('new-boot-response.json')['stdout'])==dict(guard=True,old_boot=r['old_boot'],new_boot=r['new_boot'])
off=load('vm-off.json');assert off['first_attempt_qemu_exit_code']==off['final_cut_qemu_exit_code']==137 and off['qemu_exit_code']==0 and off['vm_off'] is True
suite=(P/'python-suite.txt').read_text();assert re.search(r'Ran 744 tests in ',suite) and '\nOK\n' in suite
assert r['abrupt_vm_stop_tested'] is True
installed=rows['postcut-installed-pam-and-unit-sources-intact']['installed_files']
assert installed==s['installed_files']
assert next(c for c in s['checks'] if c['name']=='fixture-installation-durable-before-withdrawal')['installed_files']==installed
cut=load('cut.json');assert cut['signal']=='SIGKILL' and cut['pidfd_pinned'] is True and cut['guest_shutdown_requested'] is False and cut['physical_power_loss_tested'] is False
assert 'file='+off['same_disk']+',format=qcow2,if=none,id=root' in cut['command']
guard=json.loads(load('precut-guard-response.json')['stdout']);assert guard['guard'] and guard['marker_present'] and guard['helper_pids']
assert guard['boot']==s['old_boot'] and guard['pending']==s['pending'] and guard['properties']['ActiveState']=='deactivating'
assert guard['properties']['MainPID']=='0' and int(guard['properties']['Job'])>0
failed=load('failed-unflushed-setup/result.json');assert failed['passed'] is False and failed['cleanup_rc']==0 and len(failed['checks'])==5
assert load('failed-unflushed-setup/postboot-response.json')['rc']==1
journal=load('failed-unflushed-setup/peer-journal-response.json')['stdout'];assert 'file too short' in journal and 'pam_lyra_withdrawal_fixture.so' in journal
for x in load('failed-unflushed-setup/restoration-executions.json'):assert x['response']['rc']==0 and json.loads(x['response']['stdout'])['passed'] is True
for name,digest in load('failed-unflushed-setup/preboot-state.json')['source_sha256'].items():
 path=P.parent/'parental-pam-crash-recovery'/name if name=='crash-worker.py' else P/'failed-unflushed-setup'/name
 assert hashlib.sha256(path.read_bytes()).hexdigest()==digest
print('PASS: 744 tests, 15 pre-cut + 8 post-cut controls, SIGKILL to pinned QEMU, old effect refused before authorization, durable installed sources verified, four restoration readers, failed setup retained, VM OFF. Physical power loss and production remain unqualified.')
