"""Verifica evidências locais; não executa fixtures nem altera PAM."""
import hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
read=lambda n:json.loads((P/n).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
v=read('provenance.json')
for n,h in v['sha256'].items():
    assert sha(P/n)==h,n
prep,a,b=[read(n) for n in ['prepared.json','verified-recovery.json','verified-fault.json']]
assert len({x['boot_id'] for x in [prep,a,b]})==3
for result,count in [(prep,6),(a,7),(b,7)]:
    assert result['passed'] and result['full_account_protection'] is False
    assert len(result['checks'])==count
    assert len({c['name'] for c in result['checks']})==count
    assert all(c['passed'] for c in result['checks'])
meta=prep['metadata']
for name,h in meta['source_sha256'].items():
    actual={'barrier-pam-guard.c':'../parental-registry-barrier/pam-guard.c','barrier-writer.py':'../parental-registry-barrier/writer.py'}.get(name,name)
    assert sha(P/actual)==h,name
ha,hb=a['hook'],b['hook']
assert ha['files_before']==meta['before_reboot_files']
assert ha['files_after']==hb['files_before']==hb['files_after']
assert ha['recovery_executed'] and not ha['fault']
assert not hb['recovery_executed'] and hb['fault']
assert ha['enforcing']==hb['enforcing']=='Enforcing'
assert ha['source_sha256']==hb['source_sha256']==sha(P/'recover-at-boot.py')
gen=meta['generation_b']; old=meta['generation_a']
assert ha['outcome']=={old:'committed',gen:'blocked'}
assert ha['snapshot_before'][1][old]['phase']=='committed'
assert ha['snapshot_after'][1]=={}
for hook in [ha,hb]:
    assert next(r for r in hook['snapshot_after'][0] if r['generation']==gen)['state']=='recovering'
    assert hook['files_after']['.barrier-'+gen]==meta['before_reboot_files']['.barrier-'+gen]
    assert all(s['uid']==0 and s['mode']==0o600 for s in hook['files_after'].values())
for result in [a,b]:
    checks={c['name']:c for c in result['checks']}
    deny=checks['automatic-linger-manager-denied-with-exact-native-pam-cause']
    assert deny['unit']['MainPID']=='0' and deny['unit']['ExecMainStatus']=='224'
    assert 'pam_lyra_identity_registry_fixture(systemd-user:session): Experimental registry-backed admission rejected session' in deny['journal']
    ordinary=checks['ordinary-linger-manager-survives-supervised-recovery-failure']
    assert int(ordinary['unit']['MainPID'])>0 and ordinary['unit']['ActiveState']=='active'
    retry=checks['manual-manager-retry-stays-denied-without-explicit-enrollment']
    assert retry['unit']['MainPID']=='0' and retry['unit']['ExecMainStatus']=='224'
assert next(c for c in b['checks'] if c['name']=='failed-boot-recovery-keeps-durable-blocked-state')['status']=='42'
c,r=read('cleanup.json'),read('restored.json')
assert c['passed'] and all(x['passed'] for x in c['cleanup']) and all(c['restored'].values())
assert r['passed'] and all(x=='0' for x in r['units'].values()) and all(r['absent_paths'].values())
assert not r['processes'] and not r['sessions'].strip() and r['enforce']=='Permissive'
assert all(r[k] for k in ['pam_preserved','pam_mode_preserved','vendor_preserved','account_files_preserved','sshd_disabled'])
assert not r['complete_kernel_audit']
assert v['poweroff']['rc']==0 and v['qemu_exit_codes']==[0,0,0]
assert v['python_tests']==270 and not v['production_changed'] and not v['full_account_protection']
print('PASS: 20 controles nativos, hashes, dois reinícios, recuperação/falha, restauração e desligamento')
