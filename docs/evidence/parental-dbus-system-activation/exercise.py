"""Native system-bus D-Bus activation, restricted to the disposable VM.

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
files=[];routes={};activated=[]
SOURCE=Path('/root/dbus-fixture-service.c'); BINARY=Path('/usr/bin/lyra-dbus-activation-fixture')
DBUS_POLICY=Path('/etc/dbus-1/system.d/lyra-parental-dbus-fixture.conf')
BUS_PREFIX='org.lyra.ParentalDbusFixture.'
NAMES=('PlainA','GuardedA','PlainBlockedA','GuardedBlockedA','DirectA','DirectBlockedA','OrdinaryB','StaleA','NewA')
initial_bus_pid=None
assert not BINARY.exists() and not DBUS_POLICY.exists()
result=dict(kind='native-system-bus-generation-admission',checks=checks,cleanup=cleanup,
            full_account_protection=False,cron_tested=False,dbus_activation_tested=True)
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

def reload_bus():
    run(['systemctl','daemon-reload'])
    run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ReloadConfig'])
def route(short,guarded=False,direct=False):
    name=BUS_PREFIX+short;user=B if short=='OrdinaryB' else A
    service=Path('/usr/share/dbus-1/system-services',name+'.service')
    assert not service.exists()
    unit='lyra-dbus-fixture-'+short.lower()+'.service'
    text=f'[D-BUS Service]\nName={name}\nUser={user}\nExec={BINARY} {name}\n'
    if not direct:
        text+=f'SystemdService={unit}\n'
        path=Path('/run/systemd/system',unit);assert not path.exists()
        path.write_text(f'[Unit]\nDescription=Disposable parental D-Bus fixture\n[Service]\nType=dbus\nBusName={name}\nUser={user}\nKillMode=control-group\nExecStart={BINARY} {name}\n'+('PAMName=lyra-producer-fixture\n' if guarded else ''))
        files.append(path);units.append(unit);run(['restorecon',str(path)])
    service.write_text(text);files.append(service);run(['restorecon',str(service)])
    routes[short]=dict(path=service,text=text,unit=None if direct else unit,user=user,direct=direct,guarded=guarded)

def owner(short):
    result=run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','NameHasOwner','s',BUS_PREFIX+short])
    assert result['stdout'].strip() in ('b true','b false'),result
    return result['stdout'].strip()=='b true'

def probe(short,allowed=True):
    r=run(['busctl','--system','--timeout=5','call',BUS_PREFIX+short,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
    route_info=routes[short]
    if not allowed:
        unit=route_info['unit'];state=show(unit)
        log=run(['journalctl','-u',unit,'--no-pager','-o','cat'])['stdout']
        assert r['rc']!=0 and state['MainPID']=='0' and state['ExecMainStatus']=='224' and not owner(short),(r,state,log)
        exact=[line for line in log.splitlines() if 'Experimental producer registry admission rejected account' in line]
        assert exact,log
        return dict(command=r,unit=state,guard_rejection=exact)
    assert r['rc']==0,r
    sig,uid,pid=r['stdout'].split();uid=int(uid);pid=int(pid)
    assert sig=='uu' and uid==pwd.getpwnam(route_info['user']).pw_uid
    actual=Path('/proc',str(pid));uids=[int(v) for v in next(line.split()[1:] for line in (actual/'status').read_text().splitlines() if line.startswith('Uid:'))]
    assert uids==[uid]*4 and actual.joinpath('exe').resolve()==BINARY
    cgroup=(actual/'cgroup').read_text().strip();unit=cgroup.rsplit('/',1)[-1]
    if route_info['guarded']:
        assert cgroup.startswith(f'0::/user.slice/user-{uid}.slice/session-') and unit.endswith('.scope'),cgroup
        unit=route_info['unit']
    else:
        assert unit.endswith('.service') and cgroup.startswith('0::/system.slice/'),cgroup
    if route_info['direct']:
        # Discover only a live trusted fixture payload's systemd unit, not arbitrary units.
        assert unit.startswith('dbus-'),unit
        if unit not in units:units.append(unit)
        route_info['unit']=unit
    else:assert unit==route_info['unit'],(unit,route_info)
    state=show(unit)
    unit_uid=int(state['User']) if state['User'].isdecimal() else pwd.getpwnam(state['User']).pw_uid
    assert state['MainPID']==str(pid) and unit_uid==uid,state
    item=dict(short=short,pid=pid,uid=uid,uids=uids,cgroup=cgroup,unit_name=unit,unit=state)
    activated.append(item);return item

def disarm(shorts):
    for short in shorts:routes[short]['path'].unlink(missing_ok=True)
    reload_bus()

def stop_target(shorts):
    import select
    refs=[];seen=set()
    for item in activated:
        if item['short'] in shorts and item['pid'] not in seen and Path('/proc',str(item['pid'])).exists():
            seen.add(item['pid'])
            refs.append(os.pidfd_open(item['pid']))
    try:
        observations=stop_units(list(dict.fromkeys(routes[s]['unit'] for s in shorts if routes[s]['unit'])))
        poll=select.poll()
        for fd in refs:poll.register(fd,select.POLLIN)
        exited=poll.poll(3000) if refs else []
        assert len(exited)==len(refs),(exited,len(refs))
        return dict(stopped=observations,pidfds_exited=len(exited))
    finally:
        for fd in refs:os.close(fd)

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
    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),GUARD,WRITER,POLICY,SOURCE)}
    run(['setenforce','1'])
    initial_bus_pid=show('dbus.service')['MainPID']
    assert int(initial_bus_pid)>0
    run(['gcc','-Wall','-Wextra','-Werror','-O2',str(SOURCE),'-o',str(BINARY),'-lsystemd']);files.append(BINARY);run(['restorecon',str(BINARY)])
    result['payload_sha256']=hashlib.sha256(BINARY.read_bytes()).hexdigest()
    for short in NAMES:route(short,guarded=short in ('GuardedA','GuardedBlockedA','OrdinaryB','StaleA','NewA'),direct=short.startswith('Direct'))
    policy='<busconfig>\n'
    for user in (A,B):
        policy+=f'<policy user="{user}">\n'+''.join(f'<allow own="{BUS_PREFIX+short}"/>\n' for short in NAMES if routes[short]['user']==user)+'</policy>\n'
    policy+='<policy user="root">\n'+''.join(f'<allow send_destination="{BUS_PREFIX+short}"/>\n' for short in NAMES)+'</policy>\n</busconfig>\n'
    DBUS_POLICY.write_text(policy);files.append(DBUS_POLICY);run(['restorecon',str(DBUS_POLICY)]);reload_bus()
    plain=probe('PlainA');record('baseline-systemd-dbus-without-pam',**plain)
    guarded=probe('GuardedA');record('baseline-systemd-dbus-with-pam',**guarded)
    direct=probe('DirectA');record('baseline-exec-user-broker-transient-without-pam',**direct)
    ordinary=probe('OrdinaryB');record('baseline-ordinary-dbus-with-pam',**ordinary)
    try:store.begin(generation)
    except writer.StoreError as error:
        assert str(error).startswith('busy:');message=str(error)
    else:raise AssertionError('PAM D-Bus producer did not retain generation lease')
    label();record('live-dbus-pam-lease-retains-durable-barrier',error=message)
    for short,previous in (('GuardedA',guarded),('PlainA',plain),('DirectA',direct)):
        active=probe(short);assert active['pid']==previous['pid']
    record('barrier-does-not-revoke-already-owned-dbus-names',qualification='known-producer-gap')
    denied=probe('GuardedBlockedA',allowed=False);record('new-systemd-dbus-with-pam-denied',**denied)
    bypass=probe('PlainBlockedA');record('new-systemd-dbus-without-pam-bypasses-barrier',qualification='known-producer-gap',**bypass)
    direct_bypass=probe('DirectBlockedA');record('new-exec-user-dbus-bypasses-barrier',qualification='known-producer-gap',**direct_bypass)
    terminated=run(['loginctl','terminate-user',A],check=False);time.sleep(.2)
    for short,previous in (('PlainA',plain),('PlainBlockedA',bypass),('DirectA',direct),('DirectBlockedA',direct_bypass)):
        live=probe(short);assert live['pid']==previous['pid']
    record('logind-does-not-revoke-unguarded-system-bus-producers',qualification='known-producer-gap',logind=terminated)
    assert probe('OrdinaryB')['pid']==ordinary['pid']
    record('ordinary-dbus-and-shared-broker-preserved',broker_pid=show('dbus.service')['MainPID'])
    targets=[s for s in NAMES if s!='OrdinaryB']
    disarm(targets);record('fixture-activation-routes-disarmed-before-stop',routes=targets)
    stopped=stop_target(targets)
    assert all(not owner(s) for s in targets)
    assert probe('OrdinaryB')['pid']==ordinary['pid']
    record('fixture-dbus-producers-revoked-without-shared-broker-restart',**stopped)
    missing=run(['busctl','--system','--timeout=5','call',BUS_PREFIX+'PlainA','/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
    assert missing['rc'] and any(text in missing['stderr'] for text in ('ServiceUnknown','not activatable','not provided by any .service')),missing
    record('disarmed-route-cannot-reactivate',command=missing)
    store.begin(generation);store.tombstone(generation)
    new_generation=secrets.token_hex(16);store.publish(generation,dict(state='active',**binding,generation=new_generation));label()
    for short in ('StaleA','NewA'):routes[short]['path'].write_text(routes[short]['text']);run(['restorecon',str(routes[short]['path'])])
    reload_bus()
    stale=probe('StaleA',allowed=False);record('stale-generation-dbus-pam-denied',**stale)
    pam(new_generation)
    new=probe('NewA');record('new-generation-dbus-pam-admitted',**new)
    assert probe('OrdinaryB')['pid']==ordinary['pid'] and show('dbus.service')['MainPID']==initial_bus_pid
    record('ordinary-owner-and-shared-broker-survive-entire-transition',ordinary_pid=ordinary['pid'],broker_pid=initial_bus_pid)
    result['passed']=True
finally:
    def clean(name,action):
        try:action();cleanup.append(dict(name=name,passed=True))
        except Exception as error:cleanup.append(dict(name=name,passed=False,error=str(error)))
    if routes:clean('disarm-fixture-activation',lambda:disarm(list(routes)))
    if units:clean('stop-fixture-producers',lambda:stop_units(units))
    for path in reversed(files):clean('remove-'+path.name,lambda path=path:path.unlink(missing_ok=True))
    if routes:clean('reload-after-fixture-removal',reload_bus)
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
        groups_removed=not {A,B}&{g.gr_name for g in grp.getgrall()},fixtures_removed=not any(p.exists() for p in (PAM,MODULE,DIRECTORY,*files)),
        broker_preserved=initial_bus_pid is None or show('dbus.service')['MainPID']==initial_bus_pid,
        vendor_preserved=Path('/usr/lib/pam.d/systemd-user').read_bytes()==vendor,
        original_accounts_preserved=original_accounts=={name:(pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in original_accounts},
        permissive=run(['getenforce'])['stdout'].strip()=='Permissive')
    result['passed']=bool(result.get('passed') and all(r['passed'] for r in cleanup) and all(result['restored'].values()))
    Path('/root/dbus-activation-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'],result
