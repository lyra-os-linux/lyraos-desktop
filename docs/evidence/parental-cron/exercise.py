"""Real minutely cron jobs in the dedicated disposable VM only."""
import grp,hashlib,importlib.util,json,os,pwd,secrets,shutil,signal,select,subprocess,time
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'} <= set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
A,B='cronfixture','croncontrol';UID_A,UID_B,GID_A,GID_B=31300,31301,41300,41301
DIRECTORY=Path('/var/lib/lyra-parental-test');PAM=Path('/etc/pam.d/crond')
MODULE=Path('/usr/lib64/security/pam_lyra_producer_registry_fixture.so')
GUARD=Path('/root/producer-pam-account-guard.c');WRITER=Path('/root/barrier-writer.py')
POLICY=Path('/root/lyra-cron-registry.cil');SOURCE=Path('/root/cron-fixture.c')
BINARY=Path('/usr/bin/lyra-cron-identity-fixture');SYSTEM=Path('/etc/cron.d/lyra-parental-fixture')
HOME_A,HOME_B=Path('/home/cronfixture'),Path('/home/croncontrol')
checks=[];cleanup=[];created=[];groups=[];initial_pid=None
result=dict(kind='native-cronie-user-and-system-crontabs',checks=checks,cleanup=cleanup,
    full_account_protection=False,complete_kernel_audit=False,clock_modified=False)
original_accounts={name:(pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in ('parentaltest','ordinaryuser')}
vendor=Path('/usr/lib/pam.d/crond').read_bytes()
common={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/etc/pam.d').glob('common-*') if p.is_file()}
assert not any(p.exists() for p in (PAM,MODULE,DIRECTORY,BINARY,SYSTEM,HOME_A,HOME_B))
assert not {A,B}&{p.pw_name for p in pwd.getpwall()} and not {A,B}&{g.gr_name for g in grp.getgrall()}
spec=importlib.util.spec_from_file_location('writer',WRITER);writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)
module_created=state_created=policy_installed=binary_created=system_created=False

def run(args,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=40)
    row=dict(rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
    if check and p.returncode:raise RuntimeError((args,row))
    return row
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip()=='0'
def record(name,**details):
    row=dict(name=name,passed=True,**details);checks.append(row);print(json.dumps(row),flush=True)
def label():run(['chcon','-R','-t','lyra_cron_registry_state_t',str(DIRECTORY)])
def pam(gen):
    # Must precede the vendor sufficient account control.
    fragment=f'account requisite pam_lyra_producer_registry_fixture.so account=active|{A}|{UID_A}|{GID_A}|{A}|{gen}\n'
    PAM.write_bytes(fragment.encode()+vendor);PAM.chmod(0o644);run(['restorecon',str(PAM)])
def journal_cursor():
    log=run(['journalctl','-n','1','--show-cursor','--no-pager','-o','cat'])['stdout']
    return next(line.removeprefix('-- cursor: ') for line in log.splitlines() if line.startswith('-- cursor: '))
def journal_after(cursor):
    return run(['journalctl','--after-cursor='+cursor,'--no-pager','-o','cat'])['stdout']
def rows(home,kind):
    path=home/(kind+'.log')
    if not path.exists():return []
    return [dict(uid=int(uid),pid=int(pid),epoch=int(epoch)) for uid,pid,epoch in (line.split() for line in path.read_text().splitlines())]
def pid_identity(pid):
    p=Path('/proc',str(pid));lines=(p/'status').read_text().splitlines()
    uids=[int(v) for v in next(line.split()[1:] for line in lines if line.startswith('Uid:'))]
    return dict(pid=pid,uids=uids,exe=str((p/'exe').resolve()),cgroup=(p/'cgroup').read_text().strip(),
                parent=int(next(line.split()[1] for line in lines if line.startswith('PPid:'))))
def live(row):
    ident=pid_identity(row['pid']);assert ident['uids']==[row['uid']]*4 and ident['exe']==str(BINARY),ident
    return ident

def wait_tick(home,count):
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        if all(len(rows(home,k))>=count for k in ('user','system')):
            time.sleep(.3);return
        time.sleep(.2)
    raise AssertionError(dict(home=str(home),count=count,rows={k:rows(home,k) for k in ('user','system')},journal=run(['journalctl','-u','cron.service','--no-pager','-o','cat'])['stdout']))
def denied_tick(cursor,a_count,b_count):
    wait_tick(HOME_B,b_count)
    assert all(len(rows(HOME_A,k))==a_count for k in ('user','system'))
    log=journal_after(cursor)
    rejections=[line for line in log.splitlines() if 'Experimental producer registry admission rejected account' in line]
    errors=[line for line in log.splitlines() if f'({A})' in line and 'FAILED to authorize user with PAM' in line]
    assert len(rejections)==len(errors)==2,(rejections,errors,log)
    return dict(guard_rejections=rejections,cron_account_errors=errors,ordinary_count=b_count,supervised_count=a_count,journal_after_cursor=cursor)

def holders(gen):
    lease=DIRECTORY/('.lease-'+gen+'.lock');target=lease.stat();found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            owns=False
            for fd in (p/'fd').iterdir():
                try:s=fd.stat()
                except FileNotFoundError:continue
                if (s.st_dev,s.st_ino)==(target.st_dev,target.st_ino):owns=True
            if owns:found.append(pid_identity(int(p.name)))
        except FileNotFoundError:pass
    return found

def stop_payloads(pids,uid):
    refs=[]
    try:
        for pid in sorted(set(pids)):
            fd=os.pidfd_open(pid);refs.append(fd)
            ident=pid_identity(pid);assert ident['uids']==[uid]*4 and ident['exe']==str(BINARY),ident
            signal.pidfd_send_signal(fd,signal.SIGTERM)
        poll=select.poll()
        for fd in refs:poll.register(fd,select.POLLIN)
        exited=set();deadline=time.monotonic()+4
        while refs and time.monotonic()<deadline and len(exited)<len(refs):
            for fd,event in poll.poll(max(1,int((deadline-time.monotonic())*1000))):
                assert event & select.POLLIN,event
                exited.add(fd);poll.unregister(fd)
        assert len(exited)==len(refs),(len(exited),len(refs))
        return dict(payload_pidfds_exited=len(exited),signaled_uid=uid,root_signals=False)
    finally:
        for fd in refs:os.close(fd)
try:
    for name,uid,gid,home in ((A,UID_A,GID_A,HOME_A),(B,UID_B,GID_B,HOME_B)):
        assert uid not in {p.pw_uid for p in pwd.getpwall()} and gid not in {g.gr_gid for g in grp.getgrall()}
        run(['groupadd','-g',str(gid),name]);groups.append(name)
        run(['useradd','-M','-d',str(home),'-u',str(uid),'-g',str(gid),'-s','/bin/bash',name]);created.append(name)
        subprocess.run(['chpasswd'],input=name+':'+secrets.token_urlsafe(32)+'\n',text=True,capture_output=True,check=True)
        home.mkdir(mode=0o700);os.chown(home,uid,gid);run(['restorecon','-R',str(home)])
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);module_created=True;run(['restorecon',str(MODULE)])
    run(['gcc','-Wall','-Wextra','-Werror','-O2',str(SOURCE),'-o',str(BINARY)]);binary_created=True;run(['restorecon',str(BINARY)])
    DIRECTORY.mkdir(mode=0o700);state_created=True;store=writer.RegistryStore(DIRECTORY);generation=secrets.token_hex(16)
    binding=dict(user=A,uid=UID_A,gid=GID_A,group=A);store.seed([dict(state='active',**binding,generation=generation)])
    run(['semodule','-i',str(POLICY)]);policy_installed=True;label();pam(generation)
    result['source_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),GUARD,WRITER,POLICY,SOURCE)}
    result['vendor_pam_sha256']=hashlib.sha256(vendor).hexdigest();result['common_pam_sha256']=common
    result['payload_sha256']=hashlib.sha256(BINARY.read_bytes()).hexdigest()
    for name,home in ((A,HOME_A),(B,HOME_B)):
        table=Path('/root',name+'.crontab');table.write_text(f'MAILTO=""\n* * * * * {BINARY} {home}/user.log\n')
        run(['crontab','-u',name,str(table)]);table.unlink()
        spool=Path('/var/spool/cron/tabs',name)
        before_label=run(['ls','-Z',str(spool)])['stdout'].strip()
        run(['restorecon',str(spool)])
        result.setdefault('fixture_spool_labels',[]).append(dict(user=name,before=before_label,after=run(['ls','-Z',str(spool)])['stdout'].strip()))
    SYSTEM.write_text('MAILTO=""\n'+''.join(f'* * * * * {name} {BINARY} {home}/system.log\n' for name,home in ((A,HOME_A),(B,HOME_B))));system_created=True;SYSTEM.chmod(0o644);run(['restorecon',str(SYSTEM)])
    run(['setenforce','1']);run(['systemctl','start','cron.service'])
    initial_pid=run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip();assert int(initial_pid)>0
    wait_tick(HOME_A,1);wait_tick(HOME_B,1)
    originals_a=[live(rows(HOME_A,k)[0]) for k in ('user','system')]
    originals_b=[live(rows(HOME_B,k)[0]) for k in ('user','system')]
    record('baseline-real-user-and-system-crontabs-admitted',supervised=originals_a,ordinary=originals_b,cron_pid=initial_pid)
    owners=holders(generation);assert len(owners)>=2 and all(x['uids']==[0]*4 and x['exe']=='/usr/sbin/cron' for x in owners),owners
    record('root-cron-monitors-retain-generation-lease',holders=owners)
    try:store.begin(generation)
    except writer.StoreError as error:
        assert str(error).startswith('busy:');message=str(error)
    else:raise AssertionError('Cron did not retain generation lease')
    label();record('live-cron-keeps-durable-busy-barrier',error=message)
    cursor=journal_cursor();negative=denied_tick(cursor,1,2);record('blocked-next-user-and-system-cron-denied',**negative)
    terminated=run(['loginctl','terminate-user',A],check=False)
    for ident in originals_a:assert pid_identity(ident['pid'])['exe']==str(BINARY)
    record('logind-does-not-revoke-nonlogin-cron-jobs',qualification='known-producer-gap',logind=terminated)
    revoked=stop_payloads([x['pid'] for x in originals_a],UID_A)
    deadline=time.monotonic()+5
    while time.monotonic()<deadline and holders(generation):time.sleep(.05)
    assert not holders(generation)
    for ident in originals_b:assert pid_identity(ident['pid'])['exe']==str(BINARY)
    assert run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip()==initial_pid
    record('trusted-fixture-payload-stop-releases-root-monitor-leases',**revoked)
    store.begin(generation);store.tombstone(generation);new_generation=secrets.token_hex(16)
    store.publish(generation,dict(state='active',**binding,generation=new_generation));label()
    cursor=journal_cursor();stale=denied_tick(cursor,1,3);record('stale-generation-user-and-system-cron-denied',**stale)
    pam(new_generation);wait_tick(HOME_A,2);wait_tick(HOME_B,4)
    recovered=[live(rows(HOME_A,k)[1]) for k in ('user','system')]
    record('updated-generation-user-and-system-cron-admitted',supervised=recovered)
    for ident in originals_b:assert pid_identity(ident['pid'])['exe']==str(BINARY)
    assert run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip()==initial_pid
    record('ordinary-original-jobs-and-shared-daemon-preserved',ordinary=originals_b,cron_pid=initial_pid)
    result['passed']=True
finally:
    def clean(name,action):
        try:action();cleanup.append(dict(name=name,passed=True))
        except Exception as error:cleanup.append(dict(name=name,passed=False,error=str(error)))
    if system_created:clean('remove-system-fixture',lambda:SYSTEM.unlink(missing_ok=True))
    for name in created:clean('remove-user-table-'+name,lambda name=name:run(['crontab','-u',name,'-r']))
    clean('stop-native-cron',lambda:run(['systemctl','stop','cron.service']))
    clean('restore-permissive',lambda:run(['setenforce','0']))
    for name,uid,home in ((A,UID_A,HOME_A),(B,UID_B,HOME_B)):
        if name not in created:continue
        pids=[]
        for p in Path('/proc').iterdir():
            if not p.name.isdecimal():continue
            try:
                ident=pid_identity(int(p.name))
                if ident['uids']==[uid]*4 and ident['exe']==str(BINARY):pids.append(ident['pid'])
            except FileNotFoundError:pass
        if pids:clean('stop-fixture-payloads-'+name,lambda pids=pids,uid=uid:stop_payloads(pids,uid))
        for _ in range(100):
            if run(['pgrep','-u',str(uid)],check=False)['rc']!=0:break
            time.sleep(.05)
        clean('delete-account-'+name,lambda name=name:run(['userdel',name]))
        if home.exists():clean('remove-home-'+name,lambda home=home:shutil.rmtree(home))
    for name in groups:
        if name in {g.gr_name for g in grp.getgrall()}:clean('delete-group-'+name,lambda name=name:run(['groupdel',name]))
    clean('remove-pam',lambda:PAM.unlink(missing_ok=True))
    if module_created:clean('remove-module',lambda:MODULE.unlink(missing_ok=True))
    if binary_created:clean('remove-binary',lambda:BINARY.unlink(missing_ok=True))
    if state_created:clean('remove-state',lambda:shutil.rmtree(DIRECTORY))
    if policy_installed:clean('remove-policy',lambda:run(['semodule','-r','lyra-cron-registry']))
    result['restored']=dict(accounts_removed=not {A,B}&{p.pw_name for p in pwd.getpwall()},groups_removed=not {A,B}&{g.gr_name for g in grp.getgrall()},
        fixtures_removed=not any(p.exists() for p in (PAM,MODULE,DIRECTORY,BINARY,SYSTEM,HOME_A,HOME_B)),
        vendor_preserved=Path('/usr/lib/pam.d/crond').read_bytes()==vendor,
        common_preserved=common=={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in Path('/etc/pam.d').glob('common-*') if p.is_file()},
        original_accounts_preserved=original_accounts=={name:(pwd.getpwnam(name).pw_uid,pwd.getpwnam(name).pw_gid) for name in original_accounts},
        permissive=run(['getenforce'])['stdout'].strip()=='Permissive',cron_stopped=run(['systemctl','show','cron.service','-p','MainPID','--value'])['stdout'].strip()=='0')
    result['passed']=bool(result.get('passed') and all(x['passed'] for x in cleanup) and all(result['restored'].values()))
    Path('/root/cron-result.json').write_text(json.dumps(result,indent=2)+'\n')
assert result['passed'],result
