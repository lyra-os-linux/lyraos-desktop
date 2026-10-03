"""Verify archived native evidence and source identity without a running VM."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','operations.py':'../parental-operation-journal/operations.py','inventory.py':'../parental-inventory-gate/inventory.py','ownership.py':'../parental-owned-inhibitions/ownership.py','integration.py':'../parental-owned-live/integration.py','unit-adapter.py':'../parental-unit-adapter/unit-adapter.py','dbus-adapter.py':'../parental-dbus-adapter/dbus-adapter.py','namespace.py':'../parental-namespace-guard/namespace.py'}
r=read('result.json'); assert r['passed'] and r['error'] is None and r['cleanup_rc']==0 and not r['cleanup_stderr']
assert len(r['checks'])==24 and all(x['passed'] for x in r['checks'])
assert int((P/'native-exit-status').read_text())==0 and not (P/'native-stderr.log').read_bytes()
logs=(P/'native-stdout.log').read_text().splitlines()
assert [json.loads(l) for l in logs[:-1]]==r['checks']
assert json.loads(logs[-1])==dict(passed=True,checks=24,cleanup_rc=0)
for n,h in r['metadata']['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
assert r['closed_pending_discovery_qualified'] and r['closed_pending_activation_pair_tested']
for f in ('full_account_protection','all_producer_quiescence','production_adapters_qualified','pending_activation_races_qualified','production_pending_discovery_qualified','boot_route_recovery_qualified','whole_dbus_namespace_qualified','real_nss_mutations_tested','monotonic_revision_qualified','power_loss_tested','ownership_ledger_reboot_qualified'):assert r[f] is False,f
c={x['name']:x for x in r['checks']}; descriptors={}
for short in ('TargetUnit','TargetExec'):
    x=c['actual-unowned-pending-'+short];d=x['descriptor'];descriptors[short]=d
    assert not x['name_has_owner'] and d['uid']==1002 and d['uids']==[1002]*4
    assert d['pid']>0 and d['unit_state']['MainPID']==str(d['pid']) and not d['unit_state']['PAMName']
assert descriptors['TargetUnit']['unit_state']['ActiveState']=='activating'
assert descriptors['TargetExec']['unit'].startswith('dbus-')
x=c['automatic-discovery-finds-both-pending-without-live-registration']
assert x['completed_only_live']==['PeerUnit','PeerExec']
assert {a['pid'] for a in x['rows']}=={d['pid'] for d in descriptors.values()}
for row in x['rows']:
    assert row['uid']==1002 and row['uids']==[1002]*4 and row['start_ticks']>0 and row['executable']==x['version']
    d=next(d for d in descriptors.values() if d['pid']==row['pid'])
    assert row['unit']==d['unit'] and row['cgroup']==d['cgroup'] and row['argv'][1]==row['route']

assert r['closed_namespace_guard_qualified'] and not r['global_source_coverage_qualified'] and not r['transport_failure_controls_tested']
x=c['root-source-trees-and-loaded-view-bound'];assert x['roots']==['/etc/dbus-1/system.d','/usr/share/dbus-1/system-services'] and x['entry_count']==22 and x['lock_inode']>0
assert not any(n.startswith('org.lyra.NamespaceDbus.Target') for n in x['loaded_names'])
x=c['source-added-after-authorization-refuses-before-any-native-stop'];assert x['stop_count']==0 and {p['pid'] for p in x['processes']}=={d['pid'] for d in descriptors.values()}
x=c['already-present-unclassified-loaded-route-refuses-new-plan'];assert x['loaded'] and x['stop_count']==0
x=c['source-added-between-native-stops-prevents-second-stop'];assert len(x['events'])==1 and x['events'][0]['result']['rc']==0 and len(x['processes'])==1
assert x['processes'][0]['pid']==descriptors['TargetExec']['pid']
x=c['fresh-reconciled-plan-drains-native-pending-producers'];assert x['writer_excluded'] and x['pidfds_exited']==2 and not x['processes'] and len(x['events'])==2 and all(e['result']['rc']==0 for e in x['events'])
assert c['explicit-root-reconciliation-confirms-disk-and-loaded-view']['ledger']==c['discovery-and-retries-preserve-owner-and-negative-journals']['ledger']
for short in ('TargetUnit','TargetExec','TargetColdUnit','TargetColdExec'):
    x=c['retired-route-cannot-reactivate-'+short]['command'];assert x['rc']!=0 and 'not activatable' in x['stderr']
for x in c['pending-client-outcomes-recorded']['outcomes'].values():assert x['rc']==1 and 'activation request cancelled' in x['stderr']
x=c['withdrawn-user-manager-remains-denied'];assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224' and 'Experimental withdrawal admission rejected session' in x['journal']
x=c['peer-and-shared-broker-preserved'];assert x['broker_pid']==r['metadata']['broker_pid'] and x['peer_pid']==c['baseline-ordinary-1000']['unit']['MainPID']
for short in ('PeerUnit','PeerExec'):assert x['owners'][short]['pid']==c['baseline-'+short]['pid'] and x['owners'][short]['uids']==[1000]*4
cleanup=read('cleanup.json');assert cleanup['passed'] and all(x['passed'] for x in cleanup['cleanup']) and all(cleanup['restored'].values())
for name in ('ownership-restored.json','ownership-restored-independent.json','routes-restored.json','routes-restored-independent.json','restored.json'):assert read(name)['passed'],name
assert all(read('ownership-restored-independent.json')['absent'].values())
for name in ('routes-restored.json','routes-restored-independent.json'):
    x=read(name);assert all(x['absent'].values()) and not any(x['owners'].values()) and x['broker_pid']==r['metadata']['broker_pid']
    if name.endswith('independent.json'):assert not x['processes'] and x['scratch_absent']
x=read('routes-restored-independent.json');assert all(x[k] for k in ('unknown_source_absent','namespace_lock_absent','unknown_loaded_name_absent'))
x=read('restored.json');assert all(u=='0' for u in x['units'].values()) and all(x['absent_paths'].values()) and not x['processes'] and not x['sessions'].strip() and x['enforce']=='Permissive' and not x['complete_kernel_audit']
assert all(x[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert v['native_checks']==24 and v['native_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==v['python_suite_exit_code']==0 and v['failed_native_attempts']==0 and not v['production_changed']
assert v['python_tests']==538 and v['new_python_tests']==8
assert 'Ran 538 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert len(v['executions'])==4 and all(x['rc']==0 and not x['stderr'] for x in v['executions'])
print('PASS: 24 controles nativos, 538 testes Python, fontes e restauração verificadas')
assert hashlib.sha256((P/'restore-routes.py').read_bytes()+b'\n').hexdigest()==v['restore_routes_executed_sha256']
