"""Offline check of scoped native login effects and declared VM restoration."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py','password-client.py':'../parental-password/client.py','manager-session.c':'../parental-managers/session.c','lyra-registry-gdm.cil':'../parental-registry-gdm/launcher.cil','lyra-login-state.cil':'login-state.cil','restore-check.py':'restore-check-native.py'}
flags=('full_account_protection','whole_classification_qualified','all_producer_quiescence','real_nss_mutations_tested','production_adapters_qualified','monotonic_revision_qualified','power_loss_tested','full_gnome_session_tested','official_gdm_worker_qualified','all_gdm_routes_qualified','pending_authentication_tested')
for attempt,count in ((0,25),(1,2),(2,6),(3,19),(4,19)):
    prefix=f'failed-attempt-{attempt}/' if attempt else ''
    r=read(prefix+'result.json')
    assert len(r['checks'])==count and all(x['passed'] for x in r['checks'])
    assert r['cleanup_rc']==0 and all(r[f] is False for f in flags)
    assert r['passed']==(attempt==0) and int((P/(prefix+'exit-status')).read_text())==(1 if attempt else 0)
    if attempt:assert r['error'] and (P/(prefix+'stderr.log')).read_bytes()
    else:assert r['error'] is None and not(P/'stderr.log').read_bytes() and not r['automatic_greeter_recovery_qualified']
    for n,h in r['metadata']['source_sha256'].items():
        target=external.get(n,n)
        if attempt:
            if n=='native.py':target={1:'failed-attempt-1/native.py',2:'failed-attempt-2/native.py',3:'failed-attempt-4/native.py',4:'failed-attempt-4/native.py'}[attempt]
            if n=='routes.py' and attempt<=3:target='failed-attempt-2/routes.py' if attempt<=2 else 'failed-attempt-3/routes.py'
            if n=='login-common.py' and attempt<=3:target='failed-attempt-3/login-common.py'
            if n=='lyra-login-state.cil' and attempt==1:target='failed-attempt-1/login-state.cil'
        assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,(attempt,n,target)
    clean=read(prefix+'cleanup.json');login=read(prefix+'login-restored.json')
    assert clean['passed'] and all(x['passed'] for x in clean['cleanup']) and all(clean['restored'].values())
    assert login['passed'] and all(login['files'].values()) and login['vendors'] and all(login['absent'].values()) and login['policies_absent'] and all(p=='0' for p in login['units'].values())
r=read('result.json');c={x['name']:x for x in r['checks']};assert len(c)==25
for uid in (1000,1002):
    x=c[f'baseline-ordinary-{uid}'];assert x['unit']['ActiveState']=='active' and int(x['unit']['MainPID'])>0 and ':unconfined_t:' in x['context']
for n,uid in (('baseline-target-ssh',1002),('baseline-peer-ssh',1000),('peer-new-ssh-preserved',1000)):
    x=c[n];assert x['rc']==0 and 'LYRA_ENTRY_OK' in x['stdout'] and str(uid) in x['stdout'].splitlines() and ':unconfined_t:' in x['stdout']
for n,uid in (('baseline-target-gdm-password',1002),('peer-fresh-gdm-password-preserved',1000)):
    x=c[n];assert int(x['worker_pid'])>0 and x['processes'] and all(p['uids']==[uid]*4 and ':unconfined_t:' in p['context'] for p in x['processes'])
    assert any(e.get('name')=='SessionOpened' for e in x['events'])
inv=c['target-admitted-roots-and-payloads-inventoried'];assert inv['pidfds']>0 and int(inv['gdm_worker_pid'])>0
assert any(p['uids']==[0]*4 and p['comm'] in ('sshd-session','sshd-auth') for p in inv['processes'])
assert any(p['uids']==[1002]*4 for p in inv['processes'])
assert all('/user.slice/user-1002.slice/' in g for p in inv['processes'] for g in p['cgroup'])
x=c['old-multiplex-survives-admission-withdrawal'];assert x['rc']==0 and 'LYRA_MUX_COMMAND' in x['stdout']
x=c['native-target-ssh-and-gdm-revoked-peer-and-daemons-preserved'];assert not x['target_processes'] and x['pidfds_exited']==inv['pidfds'] and x['gdm_worker_exited'] and x['peer_forwarded'] and int(x['ssh_listener_pid'])>0 and int(x['gdm_pid'])>0
reset=c['explicit-gdm-display-fixture-reset-peer-ssh-preserved'];assert reset['old_gdm_pid']==x['gdm_pid'] and int(reset['new_gdm_pid'])>0 and reset['new_gdm_pid']!=reset['old_gdm_pid'] and not reset['adapter_effect'] and not reset['automatic_greeter_recovery_qualified']
for n in ('new-target-ssh-denied','new-sftp-denied','new-target-no-shell-tunnel-denied','old-multiplex-cannot-create-new-channel'):
    x=c[n];assert x['rc']!=0 and 'pam_lyra_ordinary_ssh_fixture(sshd:account): Experimental ordinary SSH admission rejected account' in x['rejection'] and 'Access denied for user ordinaryuser by PAM account configuration' in x['rejection']
x=c['new-target-gdm-password-denied'];assert not x['processes'] and x['worker_pid'] is None
assert 'pam_lyra_withdrawal_fixture(gdm-password:session): Experimental withdrawal admission rejected session' in x['rejection'] and not any(e.get('name')=='SessionOpened' for e in x['events'])
for n in ('denied-login-revocation-has-no-session-effect','changed-ssh-stack-prevents-revocation','gdm-idempotent-revoke-retains-negative-authority','changed-gdm-config-cannot-claim-inhibition','four-real-adapters-still-refuse-uncovered-producers','peer-ssh-survives-target-revocation-and-gdm-login'):assert c[n]['passed']
restored=read('restored.json');assert restored['passed'] and all(p=='0' for p in restored['units'].values()) and all(restored['absent_paths'].values()) and not restored['processes'] and not restored['sessions'].strip() and restored['enforce']=='Permissive' and not restored['complete_kernel_audit']
assert all(restored[k] for k in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
independent=read('login-restored-independent.json');assert independent==read('login-restored.json') and independent['files']['/etc/shadow-']
greeter=read('greeter-restored.json');assert greeter['passed'] and not greeter['scope_processes'] and greeter['logind_absent'] and greeter['gdm_uid']==r['metadata']['gdm_uid']
assert r['metadata']['login_paths']['/usr/libexec/gdm/gdm-session-worker']['sha256']=='40e1387811b74adcde44b8a34f03db1d032190867e1c5f4092bb9aa1362fdab8'
assert r['metadata']['diagnostic_worker_sha256']=='92a976fc0e375cd41d1a9330c650241081fd09278d464662a435200cc296704f'
diagnostic=read('failed-attempt-1/diagnostic.json');assert any('rejected account' in d['MESSAGE'] and ':sshd_session_t:' in d.get('_SELINUX_CONTEXT','') for d in diagnostic)
restore_fail=read('restore-check-failure.json')['result'];assert restore_fail['rc']==1 and 'NameError' in restore_fail['stderr']
assert v['native_checks']==25 and v['native_exit_code']==0 and v['failed_native_attempts']==4 and v['python_tests']==344 and v['new_python_tests']==10 and v['python_suite_exit_code']==0
assert 'Ran 344 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':25,'cleanup_rc':0}
assert v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed'] and not v['automatic_greeter_recovery_qualified'] and not v['all_producers_qualified']
print('PASS: 25 controles nativos, 344 testes; rotas parciais, reset GDM explícito e restauração conferidos')
