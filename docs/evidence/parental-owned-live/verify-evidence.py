"""Offline verification of two closed live catalogs, not whole-account coverage."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','inventory.py':'../parental-inventory-gate/inventory.py','operations.py':'../parental-operation-journal/operations.py','ownership.py':'../parental-owned-inhibitions/ownership.py','unit-adapter.py':'../parental-unit-adapter/unit-adapter.py','dbus-adapter.py':'../parental-dbus-adapter/dbus-adapter.py','integration.py':'integration.py','service.c':'../parental-dbus-adapter/service.c'}
all_checks={}
for phase,count in (('units',29),('dbus',28)):
    d=P/phase;r=read(phase+'/result.json')
    assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and not r['cleanup_stderr']
    assert int((d/'exit-status').read_text())==0 and not(d/'stderr.log').read_bytes()
    assert len(r['checks'])==count and all(x['passed'] for x in r['checks'])
    assert json.loads((d/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':count,'cleanup_rc':0}
    for n,h in r['metadata']['source_sha256'].items():
        path=P/external[n] if n in external else d/n
        assert hashlib.sha256(path.read_bytes()).hexdigest()==h,(phase,n)
    assert r['owned_live_producer_inhibition_qualified'] is True and r['owned_live_producer_revocation_qualified'] is True
    for f in ('full_account_protection','all_producer_quiescence','real_nss_mutations_tested','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested','ownership_ledger_reboot_qualified'):assert r[f] is False,(phase,f)
    c={x['name']:x for x in r['checks']};assert len(c)==count;all_checks[phase]=c
    family='system-units' if phase=='units' else 'dbus-activation'
    entries=c['owned-masks-prepared-before-live-adapter' if phase=='units' else 'owned-routes-prepared-before-live-adapter']['records']
    assert len(entries)==4
    owners=[]
    for n,row in entries.items():
        assert row['name']==n and row['family']==family and row['phase']=='fenced' and row['revision']==2
        assert row['owner']['identity']==dict(user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser') and row['owner']['phase']=='retired'
        assert row['protocol_digest']==r['metadata']['source_sha256']['ownership.py']
        assert row['adapter_digest']==r['metadata']['source_sha256']['unit-adapter.py' if phase=='units' else 'dbus-adapter.py']
        owners.append(row['owner'])
    assert all(x==owners[0] for x in owners)
    x=c['live-inhibition-revocation-and-retries-never-rewrite-owner-journals'];assert x['authorization_callbacks_outside_all_locks']
    assert len(x['ledger'])==5 and '.gate-1.lock' in x['ledger']
    pam=c['withdrawn-user-manager-remains-denied'];assert pam['unit']['MainPID']=='0' and pam['unit']['ExecMainStatus']=='224'
    assert 'pam_lyra_withdrawal_fixture(systemd-user:session): Experimental withdrawal admission rejected session' in pam['journal']
    assert c['catalog-changed-during-live-authorization-refused-before-reload']['passed']
    cleanup=read(phase+'/cleanup.json');assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
    a=read(phase+'/ownership-restored.json');assert a['passed'] and a['ledger_absent'] and a['inventory_absent']
    a=read(phase+'/ownership-restored-independent.json');assert a['passed'] and all(a['absent'].values())
    a=read(phase+'/restored.json');assert a['passed'] and all(x=='0' for x in a['units'].values()) and all(a['absent_paths'].values())
    assert not a['processes'] and not a['sessions'].strip() and a['enforce']=='Permissive' and not a['complete_kernel_audit']
    assert all(a[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
u=all_checks['units'];r=read('units/result.json')
for f in ('whole_classification_qualified','all_system_units_qualified','boot_mask_recovery_qualified'):assert r[f] is False
x=u['registered-timer-before-services-revoked-peer-preserved'];assert x['pidfds_exited']>0 and not x['processes'] and len(x['commands'])==4
assert x['commands'][0][2].endswith('.timer') and all(cmd[2].endswith('.service') for cmd in x['commands'][1:])
for n in u['owned-masks-prepared-before-live-adapter']['records']:
    x=u['masked-reactivation-denied-'+n];assert x['command']['rc']!=0 and 'masked' in x['command']['stderr'].lower() and x['unit']['MainPID']=='0'
assert u['peer-timer-can-reactivate-its-service']['old_pid']!=u['peer-timer-can-reactivate-its-service']['new_unit']['MainPID']
assert u['lost-owned-mask-never-recreated-by-live-adapter']['passed']
for n in ('units-restored.json','units-restored-independent.json'):
    a=read('units/'+n);assert a['passed'] and all(a['absent'].values()) and not a['scope_processes']
    assert all(x['MainPID']=='0' for x in a['units'].values())
    if n.endswith('independent.json'):assert not a['cgroup_leaks'] and a['scratch_absent']
b=all_checks['dbus'];r=read('dbus/result.json');broker=r['metadata']['broker_pid'];assert int(broker)>0
for f in ('pending_activation_races_qualified','boot_route_recovery_qualified','whole_dbus_namespace_qualified'):assert r[f] is False
x=b['registered-payloads-revoked-after-inhibition-peer-and-broker-preserved'];assert x['effects']==['reload-config','stop-payloads'] and x['pidfds_exited']==2 and not x['target_processes'] and x['broker_pid']==broker
for n in ('TargetUnit','TargetExec','TargetColdUnit','TargetColdExec'):
    x=b['retired-route-cannot-reactivate-'+n];assert x['command']['rc']!=0 and any(msg in x['command']['stderr'] for msg in ('ServiceUnknown','not activatable','not provided by any .service'))
for n in ('routes-restored.json','routes-restored-independent.json'):
    a=read('dbus/'+n);assert a['passed'] and all(a['absent'].values()) and not any(a['owners'].values()) and a['broker_pid']==broker
    if n.endswith('independent.json'):assert not a['processes'] and a['scratch_absent']
assert v['native_checks']==57 and v['python_tests']==496 and v['new_python_tests']==14 and v['failed_native_attempts']==0
assert v['native_exit_codes']==[0,0] and v['python_suite_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed']
assert 'Ran 496 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
print('PASS: 57 controles nativos, 496 testes; produtores vivos registrados e owner preservados')
