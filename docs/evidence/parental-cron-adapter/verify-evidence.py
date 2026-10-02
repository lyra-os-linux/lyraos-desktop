"""Offline integrity, bounded scope and real scheduling assertions."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
v=read('provenance.json')
for n,h in v['sha256'].items():assert hashlib.sha256((P/n).read_bytes()).hexdigest()==h,n
external={'withdrawal-pam-guard.c':'../parental-ordinary-withdrawal/pam-guard.c','withdrawal.py':'../parental-ordinary-withdrawal/withdrawal.py','coordinator.py':'../parental-coordinator/coordinator.py','ordinary-coordinator.py':'../parental-ordinary-coordinator/ordinary-coordinator.py','barrier-writer.py':'../parental-registry-barrier/writer.py','manager_adapters.py':'../parental-manager-adapters/adapters.py'}
flags=('full_account_protection','all_producer_quiescence','production_adapters_qualified','pending_admission_races_qualified','whole_cron_namespace_qualified','arbitrary_descendants_qualified','real_nss_mutations_tested','monotonic_revision_qualified','power_loss_tested','clock_modified')
for prefix,count,passed in (('',19,True),('failed-attempt-1/',7,False)):
    r=read(prefix+'result.json');assert r['passed'] is passed and len(r['checks'])==count and all(x['passed'] for x in r['checks']) and r['cleanup_rc']==0
    assert all(r[f] is False for f in flags) and int((P/(prefix+'exit-status')).read_text())==(0 if passed else 1)
    for n,h in r['metadata']['source_sha256'].items():
        target=prefix+n if prefix and n in ('native.py','fixture.py') else external.get(n,n)
        assert hashlib.sha256((P/target).read_bytes()).hexdigest()==h,n
    a=read(prefix+'cleanup.json');assert a['passed'] and all(x['passed'] for x in a['cleanup']) and all(a['restored'].values())
    a=read(prefix+'cron-restored.json');assert a['passed'] and all(a['absent'].values()) and a['cron_pid']=='0' and a['common_preserved'] and a['vendor_preserved']
a=read('failed-attempt-2/startup.json');assert a['passed'] is False and not a['checks'] and not a['fixture_setup_started'] and a['exit_code']==1
assert int((P/'failed-attempt-2/exit-status').read_text())==1 and not(P/'failed-attempt-2/stdout.log').read_bytes() and 'CONFIG' in (P/'failed-attempt-2/stderr.log').read_text()
assert read('failed-attempt-2/cleanup.json')['passed'] and read('failed-attempt-2/restored.json')['passed']
assert 'UnverifiedProducerCatalog' in (P/'failed-attempt-1/stderr.log').read_text() and not(P/'stderr.log').read_bytes()
r=read('result.json');assert r['error'] is None
c={x['name']:x for x in r['checks']};assert len(c)==19
x=c['baseline-native-user-and-system-jobs'];daemon=x['cron_pid'];assert int(daemon)>0
for name,uid in (('target',1002),('peer',1000)):
    assert len(x[name])==2
    for p in x[name]:assert p['uids']==[uid]*4 and p['exe']=='/usr/bin/lyra-cron-adapter-fixture' and '/system.slice/cron.service' in p['cgroup'] and p['pid']>0
x=c['baseline-registered-catalog-and-admission-verified'];assert len(x['tables'])==2 and all(t['uid']==0 and t['nlink']==1 and not t['mode']&0o022 for t in x['tables'].values())
x=c['registered-payload-and-root-monitor-pidfds-pinned'];assert x['payload_pidfds']==x['monitor_pidfds']==2
assert len({p['pid'] for p in x['monitors']})==2 and all(p['uids']==[0]*4 and p['exe']=='/usr/sbin/cron' and str(p['pid'])!=daemon for p in x['monitors'])
for n,peer_count in (('next-real-minute-denies-both-target-routes-peer-continues',2),('next-real-minute-cannot-reactivate-revoked-target-peer-continues',3)):
    x=c[n];assert len(x['guard_rejections'])==len(x['cron_account_errors'])==2 and x['target_count']==1 and x['peer_count']==peer_count and x['journal_cursor']
    assert all('pam_lyra_cron_ordinary_fixture(crond:account): Experimental ordinary cron admission rejected account' in l for l in x['guard_rejections'])
x=c['authorized-payload-revocation-reaps-root-monitors-without-root-signals'];assert x['payload_pidfds_exited']==x['monitor_pidfds_exited']==2 and not x['target_processes'] and x['cron_pid']==daemon
assert x['signals']==[dict(uid=1002,pids=[p['pid'] for p in c['baseline-native-user-and-system-jobs']['target']])]
assert x['peer']==c['baseline-native-user-and-system-jobs']['peer']
x=c['peer-jobs-and-shared-daemon-preserved-through-whole-matrix'];assert x['cron_pid']==daemon and x['peer']==c['baseline-native-user-and-system-jobs']['peer']
x=c['withdrawn-user-manager-remains-denied'];assert x['unit']['MainPID']=='0' and x['unit']['ExecMainStatus']=='224' and 'Experimental withdrawal admission rejected session' in x['journal'] and int(x['peer_pid'])>0
assert c['registered-cron-does-not-complete-global-coverage']['passed']
a=read('installation.json');assert a['passed'] and len(a['introduced'])==3 and a['signatures']['rc']==0 and a['signatures']['stdout'].count('digests signatures OK')==3
assert {l.split('|')[0] for l in a['introduced']}=={'cron','cronie','debianutils'}
assert hashlib.sha256((P/'packages-before.txt').read_bytes()).hexdigest()==a['before_sha256']
a=read('packages-restored.json');assert a['passed'] and a['exact_package_tuples_restored'] and all(x['rc']==0 for x in a['commands'])
a=read('cron-restored-independent.json');assert a['passed'] and all(a['absent'].values()) and not a['processes'] and a['policy_absent'] and a['common_preserved'] and a['cron_pid']=='0'
a=read('restored.json');assert a['passed'] and all(p=='0' for p in a['units'].values()) and all(a['absent_paths'].values()) and not a['processes'] and not a['sessions'].strip() and a['enforce']=='Permissive' and not a['complete_kernel_audit']
assert all(a[f] for f in ('pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'))
assert v['native_checks']==19 and v['python_tests']==404 and v['new_python_tests']==20 and v['failed_native_attempts']==2
assert v['native_exit_code']==v['python_suite_exit_code']==v['qemu_exit_code']==v['poweroff_rc']==0 and not v['production_changed']
assert 'Ran 404 tests' in (P/'python-suite.txt').read_text() and '\nOK\n' in (P/'python-suite.txt').read_text()
assert json.loads((P/'stdout.log').read_text().splitlines()[-1])=={'passed':True,'checks':19,'cleanup_rc':0}
print('PASS: 19 controles cron reais, 404 testes; proteção global continua NO-GO')
