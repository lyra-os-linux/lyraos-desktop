"""Offline integrity and behavioral checks for scoped D-Bus evidence."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py'}
r=read('result.json');assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and len(r['checks'])==24 and all(x['passed'] for x in r['checks'])
assert int((P/'exit-status').read_text())==0 and not(P/'stderr.log').read_bytes()
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
for flag in ('full_account_protection','all_producer_quiescence','production_adapters_qualified','pending_activation_races_qualified','boot_route_recovery_qualified','whole_dbus_namespace_qualified','real_nss_mutations_tested','monotonic_revision_qualified','power_loss_tested'):assert r[flag] is False,flag
c={x['name']:x for x in r['checks']};assert len(c)==24
for s in ('TargetUnit','TargetExec','PeerUnit','PeerExec'):
    x=c['baseline-'+s];uid=1002 if s.startswith('Target') else 1000
    assert x['uid']==uid and x['uids']==[uid]*4 and x['pid']>0 and x['unit_state']['MainPID']==str(x['pid']) and '/system.slice/' in x['cgroup'] and x['unit_state']['PAMName']==''
x=c['persisted-route-retirement-and-reload-preserve-existing-owners'];assert x['effects']==['reload-config'] and set(x['activatable'])=={'org.lyra.DBusAdapter.PeerUnit','org.lyra.DBusAdapter.PeerExec'}
x=c['registered-payloads-revoked-after-inhibition-peer-and-broker-preserved'];assert x['effects']==['reload-config','stop-payloads'] and x['pidfds_exited']==2 and not x['target_processes'] and x['broker_pid']==r['metadata']['broker_pid']
for s in ('TargetUnit','TargetExec','TargetColdUnit','TargetColdExec'):
    cmd=c['retired-route-cannot-reactivate-'+s]['command'];assert cmd['rc']!=0 and any(t in cmd['stderr'] for t in ('ServiceUnknown','not activatable','not provided by any .service'))
x=c['withdrawn-user-manager-remains-denied'];assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224' and 'Experimental withdrawal admission rejected session' in x['journal'] and int(x['peer_pid'])>0
assert c['registered-dbus-routes-do-not-complete-global-coverage']['passed']
a=read('retirement-controls.json');assert a['passed'] and len(a['checks'])==8 and all(x['passed'] for x in a['checks']) and not a['full_account_protection'] and not a['power_loss_tested']
for n,h in a['sources'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
cleanup=read('cleanup.json');assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
rest=read('restored.json');assert rest['passed'] and all(x=='0' for x in rest['units'].values()) and all(rest['absent_paths'].values()) and not rest['processes'] and not rest['sessions'].strip() and rest['enforce']=='Permissive' and not rest['complete_kernel_audit']
assert all(rest[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
for n in ('routes-restored.json','routes-restored-independent.json'):
    a=read(n);assert a['passed'] and all(a['absent'].values()) and not any(a['owners'].values()) and a['broker_pid']==r['metadata']['broker_pid']
a=read('routes-restored-independent.json');assert not a['processes'] and a['scratch_absent']
assert v['native_checks']==24 and v['supplemental_native_checks']==8 and v['python_tests']==384 and v['new_python_tests']==20
assert v['native_exit_code']==v['supplemental_exit_code']==v['python_suite_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed']
assert 'Ran 384 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':24,'cleanup_rc':0}
print('PASS: 24 controles D-Bus + 8 de persistência, 384 testes; proteção global continua NO-GO')
