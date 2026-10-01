"""Native system User= services/timers, restricted to the disposable VM.

Only fixture accounts and transient units. Baseline payload is sleep, not
parental MAC confinement. Does not change the host or existing system units.
"""
import grp,hashlib,importlib.util,json,os,pwd,secrets,shutil,subprocess,time
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
A,B='producerfixture','producercontrol'
DIRECTORY=Path('/var/lib/lyra-parental-test')
MODULE=Path('/usr/lib64/security/pam_lyra_producer_registry_fixture.so')
PAM=Path('/etc/pam.d/lyra-producer-fixture')
GUARD=Path('/root/producer-pam-account-guard.c');WRITER=Path('/root/barrier-writer.py')
POLICY=Path('/root/lyra-producer-registry.cil')
spec=importlib.util.spec_from_file_location('writer',WRITER)
writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)
checks,cleanup,units,created,groups=[],[],[],[],[]
result=dict(kind='native-system-user-service-timer-generation-admission',checks=checks,cleanup=cleanup,
            full_account_protection=False,cron_tested=False,dbus_activation_tested=False)
original_accounts={name:(pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in ('parentaltest','ordinaryuser')}
vendor=Path('/usr/lib/pam.d/systemd-user').read_bytes()
module_created=state_created=policy_installed=False
assert not any(p.exists() for p in (DIRECTORY,MODULE,PAM))
assert not {A,B}&{p.pw_name for p in pwd.getpwall()}
assert not {A,B}&{g.gr_name for g in grp.getgrall()}
def run(args,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=40)
    row=dict(rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
    if check and p.returncode:raise RuntimeError((args,row))
    return row
assert run(['getenforce'])['stdout'].strip()=='Permissive'
def record(name,**details):
    row=dict(name=name,passed=True,**details);checks.append(row);print(json.dumps(row),flush=True)
def show(unit):
    state=dict(line.split('=',1) for line in run(['systemctl','show',unit,'-p','MainPID','-p','ActiveState',
        '-p','ExecMainStatus','-p','User','-p','PAMName','-p','ControlGroup','-p','LoadState'])['stdout'].splitlines())
    if 'MainPID' not in state:
        assert unit.endswith('.timer') or state['LoadState']=='not-found',state
        state['MainPID']='0'  # Timer has no process; discarded service has no unit PID.
    return state

def stop_units(names):
    observations=[]
    for unit in names:
        load=run(['systemctl','show',unit,'-p','LoadState','--value'])['stdout'].strip()
        if load=='not-found':
            assert show(unit)['MainPID']=='0'
            observations.append(dict(unit=unit,already_gone=True));continue
        stopped=run(['systemctl','stop',unit],check=False)
        final=show(unit)
        if stopped['rc']:
            assert run(['systemctl','show',unit,'-p','LoadState','--value'])['stdout'].strip()=='not-found',(unit,stopped)
        assert final['MainPID']=='0' and final['ActiveState'] in ('inactive','failed'),(unit,final)
        observations.append(dict(unit=unit,command=stopped,final=final))
    return observations

def label():run(['chcon','-R','-t','lyra_producer_registry_state_t',str(DIRECTORY)])
def pam(gen):
    fragment=f"account requisite pam_lyra_producer_registry_fixture.so account=active|{A}|31200|41200|{A}|{gen}\n"
    PAM.write_bytes(fragment.encode()+vendor);PAM.chmod(0o644);run(['restorecon',str(PAM)])
def launch(name,user,guarded=False,timer=False,allowed=True):
    unit='lyra-producer-'+name
    service=unit+'.service';units.append(service)
    args=['systemd-run','--unit='+unit,'--property=User='+user,'--property=KillMode=control-group','--property=Type=exec']
    if guarded:args+=['--property=PAMName=lyra-producer-fixture']
    if timer:
        units.append(unit+'.timer');args+=['--on-active=1s','--timer-property=AccuracySec=100ms']
    args+=['/usr/bin/sleep','120']
    command=run(args,check=False)
    deadline=time.monotonic()+10
    while time.monotonic()<deadline:
        state=show(service)
        if state['ActiveState'] in ('active','failed'):break
        time.sleep(.05)
    if allowed:
        assert command['rc']==0 and state['ActiveState']=='active' and int(state['MainPID'])>0,(command,state)
        uid=int(next(line.split()[1] for line in Path('/proc',state['MainPID'],'status').read_text().splitlines() if line.startswith('Uid:')))
        assert uid==pwd.getpwnam(user).pw_uid
    else:
        assert state['MainPID']=='0' and state['ExecMainStatus']=='224' and state['ActiveState']=='failed',(command,state)
        log=run(['journalctl','-u',service,'--no-pager','-o','cat'])['stdout']
        assert 'Experimental producer registry admission rejected account' in log,log
    return service,state
try:
    for name,uid,gid in ((A,31200,41200),(B,31201,41201)):
        assert uid not in {p.pw_uid for p in pwd.getpwall()} and gid not in {g.gr_gid for g in grp.getgrall()}
        run(['groupadd','-g',str(gid),name]);groups.append(name)
        run(['useradd','-M','-u',str(uid),'-g',str(gid),'-s','/bin/bash',name]);created.append(name)
        # Generated only in guest; passed through stdin, never exported.
        subprocess.run(['chpasswd'],input=name+':'+secrets.token_urlsafe(32)+'\n',text=True,capture_output=True,check=True)
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);module_created=True
    run(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700);state_created=True
    store=writer.RegistryStore(DIRECTORY);generation=secrets.token_hex(16)
    binding=dict(user=A,uid=31200,gid=41200,group=A)
    store.seed([dict(state='active',**binding,generation=generation)])
    run(['semodule','-i',str(POLICY)]);policy_installed=True;label();pam(generation)
    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),GUARD,WRITER,POLICY)}
    run(['setenforce','1'])
    plain,plain_state=launch('plain-a',A)
    record('baseline-system-user-without-pam-admitted',unit=plain_state)
    guarded,guarded_state=launch('guarded-a',A,guarded=True)
    record('baseline-system-user-with-pam-admitted',unit=guarded_state)
    ordinary,ordinary_state=launch('guarded-b',B,guarded=True)
    record('baseline-ordinary-system-user-with-pam-admitted',unit=ordinary_state)
    try:store.begin(generation)
    except writer.StoreError as error:
        assert str(error).startswith('busy:');message=str(error)
    else:raise AssertionError('PAM producer did not retain generation lease')
    label();record('live-pam-producer-keeps-lease-and-durable-barrier',error=message)
    denied,denied_state=launch('guarded-denied-a',A,guarded=True,allowed=False)
    record('blocked-system-user-with-pam-denied',unit=denied_state)
    timer_denied,timer_denied_state=launch('timer-denied-a',A,guarded=True,timer=True,allowed=False)
    record('blocked-system-timer-with-pam-denied',unit=timer_denied_state)
    bypass,bypass_state=launch('plain-after-barrier-a',A)
    record('system-user-without-pam-bypasses-admission-barrier',qualification='known-producer-gap',unit=bypass_state)
    timer_bypass,timer_bypass_state=launch('plain-timer-after-barrier-a',A,timer=True)
    record('system-timer-without-pam-bypasses-admission-barrier',qualification='known-producer-gap',unit=timer_bypass_state)
    ordinary_timer,ordinary_timer_state=launch('timer-b',B,guarded=True,timer=True)
    record('ordinary-system-timer-with-pam-preserved',unit=ordinary_timer_state)
    terminated=run(['loginctl','terminate-user',A],check=False);time.sleep(.2)
    assert show(plain)['MainPID']==plain_state['MainPID'] and show(bypass)['MainPID']==bypass_state['MainPID']
    record('logind-does-not-revoke-system-user-producers',qualification='known-producer-gap',logind=terminated,
           plain=show(plain),bypass=show(bypass))
    # Stop only explicitly registered fixture producers and timer triggers.
    target_units=[u for u in units if u not in (ordinary,ordinary_timer,ordinary_timer.removesuffix('.service')+'.timer')]
    stopped=stop_units(target_units)
    assert all(show(u)['MainPID']=='0' for u in target_units if u.endswith('.service'))
    assert show(ordinary)['MainPID']==ordinary_state['MainPID']
    record('explicit-fixture-producer-stop-preserves-ordinary-units',stopped=stopped)
    store.begin(generation);store.tombstone(generation)
    new_generation=secrets.token_hex(16)
    store.publish(generation,dict(state='active',**binding,generation=new_generation));label()
    old,old_state=launch('stale-pam-a',A,guarded=True,allowed=False)
    record('old-pam-generation-denied-after-enrollment',unit=old_state)
    pam(new_generation)
    new,new_state=launch('new-pam-a',A,guarded=True)
    record('new-pam-generation-system-service-admitted',unit=new_state)
    new_timer,new_timer_state=launch('new-timer-a',A,guarded=True,timer=True)
    record('new-pam-generation-system-timer-admitted',unit=new_timer_state)
    result['passed']=True
finally:
    def clean(name,action):
        try:action();cleanup.append(dict(name=name,passed=True))
        except Exception as error:cleanup.append(dict(name=name,passed=False,error=str(error)))
    if units:clean('stop-transient-producers',lambda:stop_units(units))
    clean('restore-permissive',lambda:run(['setenforce','0']))
    for name in created:
        uid=pwd.getpwnam(name).pw_uid
        run(['loginctl','terminate-user',name],check=False)
        clean('stop-manager-'+name,lambda uid=uid:run(['systemctl','stop',f'user@{uid}.service',f'user-runtime-dir@{uid}.service']))
        for _ in range(100):
            if run(['pgrep','-u',str(uid)],check=False)['rc']!=0:break
            time.sleep(.05)
        clean('delete-account-'+name,lambda name=name:run(['userdel',name]))
    for name in groups:
        if name in {g.gr_name for g in grp.getgrall()}:clean('delete-group-'+name,lambda name=name:run(['groupdel',name]))
    clean('remove-pam-fixture',lambda:PAM.unlink(missing_ok=True))
    if module_created:clean('remove-module',lambda:MODULE.unlink(missing_ok=True))
    if state_created:clean('remove-state',lambda:shutil.rmtree(DIRECTORY))
    if policy_installed:clean('remove-policy',lambda:run(['semodule','-r','lyra-producer-registry']))
    result['restored']=dict(accounts_removed=not {A,B}&{p.pw_name for p in pwd.getpwall()},
        groups_removed=not {A,B}&{g.gr_name for g in grp.getgrall()},fixtures_removed=not any(p.exists() for p in (PAM,MODULE,DIRECTORY)),
        vendor_preserved=Path('/usr/lib/pam.d/systemd-user').read_bytes()==vendor,
        original_accounts_preserved=original_accounts=={name:(pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in original_accounts},
        permissive=run(['getenforce'])['stdout'].strip()=='Permissive')
    result['passed']=bool(result.get('passed') and all(r['passed'] for r in cleanup) and all(result['restored'].values()))
    Path('/root/producer-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'],result
