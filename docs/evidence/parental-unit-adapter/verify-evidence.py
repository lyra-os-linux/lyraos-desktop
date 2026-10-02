"""Offline inspection of the registered-unit matrix and scoped restoration."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py'}
flags=('full_account_protection','whole_classification_qualified','all_producer_quiescence','real_nss_mutations_tested','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested','all_system_units_qualified','boot_mask_recovery_qualified')
for initial,count in ((False,25),(True,10)):
    prefix='failed-attempt-1/' if initial else '';r=read(prefix+'result.json')
    assert len(r['checks'])==count and all(c['passed'] for c in r['checks']) and r['cleanup_rc']==0
    assert all(r[f] is False for f in flags) and r['passed']==(not initial)
    assert int((P/(prefix+'exit-status')).read_text())==(1 if initial else 0)
    for n,h in r['metadata']['source_sha256'].items():
        target='failed-attempt-1/native.py' if initial and n=='native.py' else external.get(n,n)
        assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,n
    cleanup=read(prefix+'cleanup.json');units=read(prefix+'units-restored.json')
    assert cleanup['passed'] and all(c['passed'] for c in cleanup['cleanup']) and all(cleanup['restored'].values())
    assert units['passed'] and all(units['absent'].values()) and not units['scope_processes'] and all(c['MainPID']=='0' for c in units['units'].values())
assert 'TypeError' in (P/'failed-attempt-1/stderr.log').read_text() and not(P/'stderr.log').read_bytes()
r=read('result.json');assert r['error'] is None
c={x['name']:x for x in r['checks']};assert len(c)==25
prefix='lyra-unit-adapter-';targets=[prefix+'target-'+s for s in ('plain.service','guarded.service','tick.service','tick.timer')]
peer=prefix+'peer-plain.service';tick=prefix+'peer-tick.service'
for name in targets[:3]+[peer,tick]:
    x=c['baseline-'+name]['unit'];assert int(x['MainPID'])>0 and x['ActiveState']=='active' and '/system.slice/' in x['ControlGroup']
    assert x['User']==('ordinaryuser' if name in targets else 'installeduser')
x=c['logind-withdrawal-does-not-revoke-no-pam-system-producers']
for n in (targets[0],targets[2]):assert x['units'][n]['MainPID']==c['baseline-'+n]['unit']['MainPID']
inv=c['registered-system-scope-processes-pinned'];assert inv['processes'] and inv['pidfds']==len(inv['processes'])
x=c['persistent-masks-do-not-imply-old-processes-stopped'];assert set(x['masks'])==set(targets) and all(s=='/dev/null' for s in x['masks'].values()) and all(u['LoadState']=='masked' for u in x['units'].values())
assert x['units'][targets[0]]['MainPID']==c['baseline-'+targets[0]]['unit']['MainPID']
x=c['registered-timer-before-services-revoked-peer-preserved'];assert x['commands']==[['systemctl','stop',targets[3]],*[['systemctl','stop',n] for n in targets[:3]]]
assert x['pidfds_exited']==inv['pidfds'] and not x['processes'] and all(u['MainPID']=='0' for u in x['target_units'].values())
assert x['peer_unit']['MainPID']==c['baseline-'+peer]['unit']['MainPID']
for n in targets:
    x=c['masked-reactivation-denied-'+n];assert x['command']['rc']!=0 and 'masked' in x['command']['stderr'].lower() and x['unit']['MainPID']=='0'
x=c['peer-timer-can-reactivate-its-service'];assert int(x['new_unit']['MainPID'])>0 and x['new_unit']['MainPID']!=x['old_pid'] and x['new_unit']['User']=='installeduser'
x=c['withdrawn-user-manager-remains-denied'];assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224' and 'Experimental withdrawal admission rejected session' in x['journal'] and int(x['peer_pid'])>0
for n in ('inhibition-denied-without-masks-or-command-effects','unregistered-unit-refused-even-without-processes','changed-producer-source-refused','revocation-denied-leaves-active-process-and-masks','no-target-reactivation-after-timer-window','lost-mask-refused-even-with-zero-processes','authorized-mask-repair-and-idempotent-revoke-keep-negative-authority','scoped-units-do-not-satisfy-all-producer-coverage'):assert c[n]['passed']
supp=read('mask-controls.json');assert supp['passed'] and len(supp['checks'])==6 and all(x['passed'] for x in supp['checks']) and supp['scratch_removed'] and supp['enforce']=='Permissive'
for n,h in supp['source_sha256'].items():assert hashlib.sha256((P/external.get(n,n)).read_bytes()).hexdigest()==h,n
restored=read('restored.json');assert restored['passed'] and all(p=='0' for p in restored['units'].values()) and all(restored['absent_paths'].values()) and not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive' and not restored['complete_kernel_audit']
assert all(restored[n] for n in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
ind=read('units-restored-independent.json');assert ind['passed'] and all(ind['absent'].values()) and not ind['scope_processes'] and not ind['cgroup_leaks'] and ind['scratch_absent']
assert v['native_checks']==25 and v['supplemental_native_checks']==6 and v['native_exit_code']==0 and v['supplemental_exit_code']==0 and v['python_tests']==364 and v['new_python_tests']==20 and v['python_suite_exit_code']==0
assert 'Ran 364 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':25,'cleanup_rc':0}
assert v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed'] and not v['all_system_units_qualified']
print('PASS: 25 controles nativos + 6 de filesystem, 364 testes; cobertura parcial mantida')
