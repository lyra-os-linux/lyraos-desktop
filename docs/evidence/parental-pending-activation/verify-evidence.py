"""Offline verification of two actual pending producers and refusal paths."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','operations.py':'../parental-operation-journal/operations.py','inventory.py':'../parental-inventory-gate/inventory.py','ownership.py':'../parental-owned-inhibitions/ownership.py','integration.py':'../parental-owned-live/integration.py','unit-adapter.py':'../parental-unit-adapter/unit-adapter.py','dbus-adapter.py':'../parental-dbus-adapter/dbus-adapter.py'}
r=read('result.json');assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and not r['cleanup_stderr']
assert len(r['checks'])==28 and all(x['passed'] for x in r['checks'])
assert int((P/'native-exit-status').read_text())==0 and not(P/'native-stderr.log').read_bytes()
logs=(P/'native-stdout.log').read_text().splitlines();assert [json.loads(l) for l in logs[:-1]]==r['checks']
assert json.loads(logs[-1])==dict(passed=True,checks=28,cleanup_rc=0)
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
assert r['closed_pending_activation_pair_tested'] and r['transport_failure_controls_tested']
for f in ('full_account_protection','all_producer_quiescence','production_adapters_qualified','pending_activation_races_qualified','production_pending_discovery_qualified','boot_route_recovery_qualified','whole_dbus_namespace_qualified','real_nss_mutations_tested','monotonic_revision_qualified','power_loss_tested','ownership_ledger_reboot_qualified'):assert r[f] is False,f
c={x['name']:x for x in r['checks']};descriptors={}
for short in ('TargetUnit','TargetExec'):
    x=c['actual-pending-activation-before-name-'+short];d=x['descriptor'];descriptors[short]=d
    assert x['client_pending'] and not x['name_has_owner'] and x['client_pid']>0
    assert d['uid']==1002 and d['uids']==[1002]*4 and d['pid']>0 and d['unit_state']['MainPID']==str(d['pid']) and not d['unit_state']['PAMName']
    assert '/system.slice/' in d['cgroup']
assert descriptors['TargetUnit']['unit_state']['ActiveState']=='activating'
assert descriptors['TargetExec']['unit'].startswith('dbus-')
records=c['owned-retirements-do-not-discard-existing-pending-requests']['records'];assert len(records)==4
for name,row in records.items():
    assert row['name']==name and row['family']=='dbus-activation' and row['phase']=='fenced' and row['revision']==2
    assert row['owner']['identity']['uid']==1002 and row['owner']['phase']=='retired' and row['effect']==row['original']
    assert row['protocol_digest']==r['metadata']['source_sha256']['ownership.py'] and row['adapter_digest']==r['metadata']['source_sha256']['dbus-adapter.py']
assert c['owned-retirements-do-not-discard-existing-pending-requests']['authorization_callbacks_outside_all_locks']
assert {x['pid'] for x in c['withdrawal-does-not-revoke-pending-no-pam-producers']['processes']}=={d['pid'] for d in descriptors.values()}
assert c['reload-transport-failure-refuses-success-retaining-physical-retirements']['command']['rc']!=0
assert c['actual-stop-request-failure-refuses-quiescence']['command']['rc']!=0
assert c['inflight-systemd-payload-can-acquire-name-after-route-retirement']['owner']
x=c['legacy-completed-only-stop-misses-exec-race-but-gate-refuses-success'];assert x['owner'] and x['descriptor']==descriptors['TargetExec'] and {p['pid'] for p in x['remaining']}=={descriptors['TargetExec']['pid']}
x=c['root-fixture-registers-verified-pinned-exec-observation'];assert x['descriptor']==descriptors['TargetExec'] and x['pending_pidfd_still_live']
x=c['authorized-stop-with-pending-observation-revokes-both-payloads'];assert x['pidfds_exited']==2 and not x['processes'];ledger=x['ledger']
for name in ('reload-transport-failure-refuses-success-retaining-physical-retirements','inflight-systemd-payload-can-acquire-name-after-route-retirement','legacy-completed-only-stop-misses-exec-race-but-gate-refuses-success','authorized-idempotent-retries-keep-journals-and-negative-authority'):assert c[name]['ledger']==ledger,name
assert len(ledger)==5 and '.gate-1.lock' in ledger
for short in ('TargetUnit','TargetExec','TargetColdUnit','TargetColdExec'):
    result=c['post-revocation-route-cannot-reactivate-'+short]['command'];assert result['rc']!=0 and any(msg in result['stderr'] for msg in ('ServiceUnknown','not activatable','not provided by any .service'))
for x in c['original-pending-client-outcomes-archived']['outcomes'].values():assert x['rc']==1 and 'activation request cancelled' in x['stderr']
pam=c['withdrawn-user-manager-remains-denied'];assert pam['unit']['MainPID']=='0' and pam['unit']['ExecMainStatus']=='224' and 'Experimental withdrawal admission rejected session' in pam['journal']
x=c['peer-owners-manager-and-shared-broker-survive-pending-matrix'];assert x['broker_pid']==r['metadata']['broker_pid'] and x['peer_pid']==c['baseline-ordinary-1000']['unit']['MainPID']
for short in ('PeerUnit','PeerExec'):assert x['owners'][short]['pid']==c['baseline-'+short]['pid'] and x['owners'][short]['uids']==[1000]*4
cleanup=read('cleanup.json');assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
for name in ('ownership-restored.json','ownership-restored-independent.json','routes-restored.json','routes-restored-independent.json','restored.json'):assert read(name)['passed'],name
x=read('ownership-restored-independent.json');assert all(x['absent'].values())
for name in ('routes-restored.json','routes-restored-independent.json'):
    x=read(name);assert all(x['absent'].values()) and not any(x['owners'].values()) and x['broker_pid']==r['metadata']['broker_pid']
    if name.endswith('independent.json'):assert not x['processes'] and x['scratch_absent']
x=read('restored.json');assert all(u=='0' for u in x['units'].values()) and all(x['absent_paths'].values()) and not x['processes'] and not x['sessions'].strip() and x['enforce']=='Permissive' and not x['complete_kernel_audit']
assert all(x[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert v['native_checks']==28 and v['native_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and v['failed_native_attempts']==0 and not v['production_changed']
assert v['python_baseline_tests']==496 and v['python_baseline_reused'] and 'Ran 496 tests' in (P/'../parental-owned-live/python-suite.txt').read_text()
assert all(x['rc']==0 and not x['stderr'] for x in v['executions'])
print('PASS: 28 controles; pending producers e falhas recusam quiescência indevida')
