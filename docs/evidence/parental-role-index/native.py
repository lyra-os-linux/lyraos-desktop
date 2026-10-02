"""Real user-manager PAM with a persistent role index; marked VM only."""
from common import *
import secrets,subprocess,shutil
ROLES=Path('/var/lib/lyra-parental-roles-test');INDEX=ROLES/'role-index'
checks=[]
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,CONFIG,ROLES))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1002,1003))
assert all(not Path('/var/lib/systemd/linger',n).exists() for n in ('parentaltest','ordinaryuser'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1003,'parentaltest'),(1002,'ordinaryuser')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),
    account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'cleanup.py')})
save(meta);passed=False;error=None

def write_roles(rows):
    lines=['LYRA-ROLE-INDEX-V1\n']
    for r in rows:
        lines.append('|'.join(str(r[k]) for k in ('state','user','uid','gid','group','generation'))+'\n')
    fd=os.open(ROLES,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:writer.RegistryStore._atomic(fd,'role-index',''.join(lines).encode())
    finally:os.close(fd)
    run(['restorecon','-R',str(ROLES)])

def restore_state(data):
    fd=os.open(DIRECTORY,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:writer.RegistryStore._atomic(fd,'identity-registry',data)
    finally:os.close(fd)
    run(['restorecon',str(DIRECTORY/'identity-registry')])
    assert (DIRECTORY/'identity-registry').stat().st_mode&0o777==0o600
    assert (DIRECTORY/'identity-registry').read_bytes()==data

def attempt(name,uid,allowed):
    run(['systemctl','reset-failed',f'user@{uid}.service'],check=False)
    cursor=json.loads(run(['journalctl','-n','1','-o','json'])['stdout'])['__CURSOR']
    child=run(['systemctl','start',f'user@{uid}.service'],check=False);unit=show(uid)
    journal=run(['journalctl','-b','--after-cursor='+cursor,'-u',f'user@{uid}.service','--no-pager','-o','cat'])['stdout']
    ctx=None
    if allowed:
        assert child['rc']==0 and unit['ActiveState']=='active' and int(unit['MainPID'])>0,(name,child,unit,journal)
        ctx=context(uid)
        assert ctx==CONTEXT if uid==1003 else ':unconfined_t:' in ctx,ctx
    else:
        assert child['rc']!=0 and unit['MainPID']=='0' and unit['ExecMainStatus']=='224',(name,child,unit,journal)
        assert 'pam_lyra_role_registry_fixture(systemd-user:session): Experimental role-index admission rejected session' in journal,journal
    record(checks,name,uid=uid,allowed=allowed,unit=unit,context=ctx,journal=journal)
    stop(uid);run(['systemctl','stop',f'user-runtime-dir@{uid}.service']);drain(uid,'parentaltest' if uid==1003 else 'ordinaryuser')

try:
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux'])
    MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700);run(['restorecon',str(DIRECTORY)])
    ROLES.mkdir(mode=0o700)
    store=writer.RegistryStore(DIRECTORY);generation=secrets.token_hex(16)
    protected=dict(state='active',**IDENTITY,generation=generation)
    ordinary=dict(state='ordinary',user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser',generation=secrets.token_hex(16))
    store.seed([protected]);roles=[protected,ordinary];write_roles(roles);install_pam(generation)
    assert 'account=' not in PAM.read_text() and 'pam_succeed_if' not in PAM.read_text().split('pam_lyra_role_registry_fixture')[0].split(VENDOR.read_text())[-1]
    run(['setenforce','1']);state=(DIRECTORY/'identity-registry').read_bytes()
    attempt('persistent-protected-role-admits-native-manager',1003,True)
    attempt('explicit-ordinary-role-admits-native-manager',1002,True)
    for fault in ('missing-state','corrupt-state','missing-protected-role','missing-index','corrupt-index','unsafe-index-mode','wrong-ordinary-role','partial-role-identity'):
        write_roles(roles)
        restore_state(state)
        assert INDEX.stat().st_mode&0o777==0o600
        assert (DIRECTORY/'identity-registry').stat().st_mode&0o777==0o600
        try:
            if fault=='missing-state':(DIRECTORY/'identity-registry').unlink()
            elif fault=='corrupt-state':(DIRECTORY/'identity-registry').write_bytes(b'corrupt\n')
            elif fault=='missing-protected-role':write_roles([ordinary])
            elif fault=='missing-index':INDEX.unlink()
            elif fault=='corrupt-index':INDEX.write_bytes(b'corrupt\n')
            elif fault=='unsafe-index-mode':INDEX.chmod(0o644)
            elif fault=='wrong-ordinary-role':write_roles([dict(protected,state='ordinary'),ordinary])
            elif fault=='partial-role-identity':write_roles([dict(protected,gid=1005),ordinary])
            attempt(fault+'-protected-denied',1003,False)
            allow_ordinary=fault not in {'missing-index','corrupt-index','unsafe-index-mode'}
            attempt(fault+('-ordinary-preserved' if allow_ordinary else '-ordinary-denied-availability-gap'),1002,allow_ordinary)
        finally:
            write_roles(roles);restore_state(state)
    attempt('final-protected-role-restored',1003,True)
    attempt('final-ordinary-role-restored',1002,True)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    if ROLES.exists():shutil.rmtree(ROLES)
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=90)
    row=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,
        cleanup_stderr=cleanup.stderr,full_account_protection=False,whole_classification_qualified=False,
        missing_classifier_preserves_ordinary=False,real_nss_mutations_tested=False,
        generation=(generation if 'generation' in globals() else None))
    (BASE/'result.json').write_text(json.dumps(row,indent=2)+'\n')
    print(json.dumps({'passed':row['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}))
    assert cleanup.returncode==0,cleanup.stderr
