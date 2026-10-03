from bridge import *
from fixture import *
import secrets,shutil,subprocess
checks=[]
from owned_common import *
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not any(p.exists() for p in (DIRECTORY,MODULE,UNIT,CONFIG,ROLES,PROOFS))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1000,1002,1003))
assert not any(Path('/var/lib/systemd/linger',n).exists() for n in ('installeduser','ordinaryuser','parentaltest'))
BASE.mkdir(mode=0o700,exist_ok=True)
for uid,name in ((1000,'installeduser'),(1002,'ordinaryuser'),(1003,'parentaltest')):drain(uid,name)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'helper.py',BASE/'state.py',BASE/'bridge.py',BASE/'withdrawal.py',BASE/'coordinator.py',BASE/'ordinary-coordinator.py',BASE/'manager_adapters.py',BASE/'cleanup.py',BASE/'restore-check.py')})
meta['source_sha256'].update({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (BASE/'fixture.py',BASE/'inventory.py',BASE/'operations.py',BASE/'child.py',BASE/'op-common.py',BASE/'ownership.py',BASE/'owned-common.py',BASE/'unit-adapter.py',BASE/'dbus-adapter.py')})
save(meta);passed=False;error=None;pins=[]

def expect(code,action):
    try:action()
    except oc.GateError as e:assert e.code==code,(e.code,code)
    else:raise AssertionError('expected '+code)

def stop_target():
    stop(1002);run(['systemctl','stop','user-runtime-dir@1002.service']);drain(1002,'ordinaryuser')

def reset_case():
    assert show(1002)['MainPID']=='0' and not uid_processes(1002)
    for n in ('.deny-1002','.withdrawal-1002.json'):(PROOFS/n).unlink(missing_ok=True)
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    write_rows(PROOFS,'1002',[ordinary])

try:
    run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
    DIRECTORY.mkdir(mode=0o700);ROLES.mkdir(mode=0o700);PROOFS.mkdir(mode=0o700)
    for uid in (1000,1002,1003):
        fd=os.open(PROOFS/f'.gate-{uid}.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(PROOFS,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    generation=secrets.token_hex(16);protected=dict(state='active',**IDENTITY,generation=generation)
    ordinary=dict(state='ordinary',user='ordinaryuser',uid=1002,gid=1003,group='ordinaryuser',generation=secrets.token_hex(16))
    peer=dict(state='ordinary',user='installeduser',uid=1000,gid=1001,group='installeduser',generation=secrets.token_hex(16))
    writer.RegistryStore(DIRECTORY).seed([protected]);run(['restorecon','-R',str(DIRECTORY)])
    write_rows(ROLES,'role-index',[protected,ordinary,peer])
    for row in (ordinary,peer):write_rows(PROOFS,str(row['uid']),[row])
    install_pam(generation);run(['setenforce','1'])
    for uid in (1000,1002):
        run(['systemctl','start',f'user@{uid}.service']);assert context(uid).startswith('unconfined_u:unconfined_r:unconfined_t:')
        record(checks,f'baseline-ordinary-{uid}',unit=show(uid),context=context(uid))
    peer_pid=show(1000)['MainPID'];old_pid=show(1002)['MainPID'];peer_proof=(PROOFS/'1000').read_bytes()
    create_inventory()
    SCRATCH.mkdir(mode=0o700)
    for path in (LEDGER,MASKS,ROUTES):path.mkdir(mode=0o700)
    fd=os.open(LEDGER/'.gate-1.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(LEDGER,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    points=('intent-synced','effect-synced','fenced-journal-synced')
    masks=[('lyra-owner-'+str(n)+'.service',hashlib.sha256(('User=ordinaryuser\nFixture='+str(n)).encode()).hexdigest()) for n in range(4)]
    routes=[]
    for n in range(5):
        name='org.lyra.Owner'+str(n);data=('[D-BUS Service]\nName='+name+'\nExec=/usr/bin/false\nUser=ordinaryuser\n').encode()
        routes.append((name,hashlib.sha256(data).hexdigest()));(ROUTES/(name+'.service')).write_bytes(data)
    meta.update(mask_routes=masks,dbus_routes=routes);save(meta)
    def catalog(uid):
        row=manifest(uid,hashlib.sha256((BASE/'manager_adapters.py').read_bytes()).hexdigest(),hashlib.sha256(GUARD.read_bytes()).hexdigest())
        for family,items,file in (('system-units',masks,'unit-adapter.py'),('dbus-activation',routes,'dbus-adapter.py')):
            row['producers'][family]=dict(state='registered',adapter_digest=hashlib.sha256((BASE/file).read_bytes()).hexdigest(),routes=[dict(id=name,digest=digest) for name,digest in items])
        return row
    publish(1002,catalog(1002));publish(1000,catalog(1000));stop_target()
    operation=secrets.token_hex(16);owner=factory();assert owner.begin(owner.plan(1002,operation),lambda _:True)=='AdmissionWithdrawnNoQuiescence'
    peer_state=state()['1000'];peer_catalog=(CATALOG/'1000.json').read_bytes();barrier=(PROOFS/'.deny-1002').read_bytes()
    record(checks,'owned-negative-admission-ready-before-producer-effects',owner=ops.decode((PROOFS/'.operation-1002.json').read_bytes()))
    gate=owned_factory();crashes=[]
    def snapshot_ledger():return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),inode=p.stat().st_ino,mode=p.stat().st_mode&0o777) for p in LEDGER.iterdir()}
    def peer_ok():return state()['1000']==peer_state and (CATALOG/'1000.json').read_bytes()==peer_catalog and show(1000)['MainPID']==peer_pid
    for family,items in (('system-units',masks),('dbus-activation',routes)):
        for n,point in enumerate(points):
            key=(family,items[n][0]);before=gate.plan(1002,operation,key)
            child=run(['/usr/bin/python3',str(BASE/'child.py'),operation,family,key[1],point],check=False);assert child['rc']==91 and not child['stderr'],child
            current=gate.plan(1002,operation,key);row=owned.decode(current.entry)
            assert row['owner']==ops.decode((PROOFS/'.operation-1002.json').read_bytes()) and (PROOFS/'.deny-1002').read_bytes()==barrier
            assert row['phase']==('fenced' if point=='fenced-journal-synced' else 'intent')
            record(checks,'durable-resource-crash-'+family+'-'+point,key=key,child_rc=child['rc'],owner=row,resource_state=json.loads(current.resource_state))
            deny_attempt(checks,'pam-barrier-after-'+family+'-'+point)
            old=snapshot_ledger();expect('Denied',lambda:gate.resume(1002,operation,key,lambda _:False));assert snapshot_ledger()==old
            calls=[]
            def auth(row):calls.append(row);return True
            fresh=owned_factory();assert fresh.resume(1002,operation,key,auth)=='OwnedFilesystemInhibitionNoQuiescence' and len(calls)==1
            finished=fresh.plan(1002,operation,key);done=owned.decode(finished.entry);assert done['phase']=='fenced' and done['revision']==2 and done['owner']==row['owner']
            old=snapshot_ledger();assert fresh.resume(1002,operation,key,lambda _:True)=='OwnedFilesystemInhibitionNoQuiescence' and snapshot_ledger()==old and peer_ok()
            record(checks,'authorized-resource-resume-'+family+'-'+point,owner=done,peer_pid=peer_pid,peer_preserved=True,authorization_calls=len(calls),idempotent_retry_readonly=True)
            crashes.append(dict(family=family,point=point,name=key[1],child_rc=child['rc']))
    # Simulate the real exclusive-hardlink intermediate under an already fsynced
    # intent. The backend keeps the original inode and never recreates a source.
    key=('dbus-activation',routes[3][0]);child=run(['/usr/bin/python3',str(BASE/'child.py'),operation,*key,'intent-synced'],check=False);assert child['rc']==91 and not child['stderr']
    route=d.Route(*routes[3]);a,b=d.RetiredRoutes.names(route);inode=(ROUTES/a).stat().st_ino
    os.link(ROUTES/a,ROUTES/b);fd=os.open(ROUTES,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    assert d.RetiredRoutes(ROUTES).inspect(route)=='partial'
    assert gate.resume(1002,operation,key,lambda _:True)=='OwnedFilesystemInhibitionNoQuiescence' and not (ROUTES/a).exists() and (ROUTES/b).stat().st_ino==inode
    record(checks,'owned-hardlink-intermediate-resumes-original-inode',inode=inode,fixture_intermediate_created_explicitly=True)
    # Unowned effects cannot be claimed, even with the expected shape/digest.
    key=('system-units',masks[3][0]);(MASKS/key[1]).symlink_to('/dev/null');old=snapshot_ledger()
    expect('UnownedInhibition',lambda:gate.plan(1002,operation,key));assert snapshot_ledger()==old and os.readlink(MASKS/key[1])=='/dev/null'
    record(checks,'preexisting-unowned-mask-refused-without-ledger-write')
    key=('dbus-activation',routes[4][0]);d.RetiredRoutes(ROUTES).retire((d.Route(*routes[4]),));old=snapshot_ledger()
    expect('UnownedInhibition',lambda:gate.plan(1002,operation,key));assert snapshot_ledger()==old
    record(checks,'preexisting-unowned-retirement-refused-without-ledger-write')
    key=('system-units',masks[0][0]);plan=gate.plan(1002,operation,key);old=snapshot_ledger()
    expect('Conflict',lambda:gate.resume(1002,'0'*32,key,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))))
    expect('Denied',lambda:gate.resume(1002,operation,key,lambda _:1));assert snapshot_ledger()==old
    row=catalog(1002);changed=dict(row,revision=2);publish(1002,changed)
    expect('Conflict',lambda:gate.resume(1002,operation,key,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))));assert snapshot_ledger()==old
    publish(1002,row)
    record(checks,'operation-auth-and-catalog-refusals-preserve-existing-fences')
    # Missing/corrupt ledger metadata never triggers implicit ownership adoption.
    name=next(p for p in LEDGER.iterdir() if p.name.endswith('.json') and owned.decode(p.read_bytes())['name']==key[1]);original=name.read_bytes();name.unlink()
    expect('UnownedInhibition',lambda:gate.plan(1002,operation,key));assert (MASKS/key[1]).is_symlink()
    name.write_bytes(original);name.chmod(0o600)
    record(checks,'lost-owner-record-never-adopts-present-mask')
    name.write_bytes(b'{}');expect('InvalidFenceJournal',lambda:gate.plan(1002,operation,key));assert (MASKS/key[1]).is_symlink();name.write_bytes(original)
    record(checks,'corrupt-fence-journal-keeps-mask-and-admission-barrier')
    # A completed fence missing or replaced requires operator recovery, not
    # silent recreation. Replacement is an explicit root fixture divergence.
    p=MASKS/key[1];p.unlink();expect('ResourceChanged',lambda:gate.plan(1002,operation,key));assert not p.exists()
    record(checks,'completed-mask-removal-never-auto-recreated')
    # Preserve the original inode via an exclusive same-directory rename,
    # then put a replacement at the resource path and test identity checking.
    key=('system-units',masks[1][0]);p=MASKS/key[1];backup=MASKS/'saved-mask';p.rename(backup);p.symlink_to('/dev/null')
    expect('ResourceChanged',lambda:gate.plan(1002,operation,key));p.unlink();backup.rename(p)
    record(checks,'completed-mask-replacement-inode-refused')
    key=('dbus-activation',routes[0][0]);route=d.Route(*routes[0]);a,b=d.RetiredRoutes.names(route);p=ROUTES/b;backup=ROUTES/'saved-definition';p.rename(backup);p.write_bytes(backup.read_bytes())
    expect('ResourceChanged',lambda:gate.plan(1002,operation,key));p.unlink();backup.rename(p)
    record(checks,'replaced-retired-definition-inode-refused')
    key=('system-units',masks[1][0]);lock=LEDGER/'.gate-1.lock';inode=lock.stat().st_ino;backup=LEDGER/'lock-save';lock.rename(backup)
    try:
        try:gate.plan(1002,operation,key)
        except oc.GateError as e:assert e.code in ('RecoveryRequired','StorageFailure')
        else:raise AssertionError('missing ledger lock auto-created')
        assert not lock.exists()
    finally:backup.rename(lock)
    assert lock.stat().st_ino==inode
    record(checks,'missing-global-ledger-lock-never-created',lock_inode=inode)
    name=next(p for p in LEDGER.iterdir() if p.name.endswith('.json') and owned.decode(p.read_bytes())['name']==key[1]);name.chmod(0o640)
    expect('StorageFailure',lambda:gate.plan(1002,operation,key));name.chmod(0o600)
    record(checks,'group-readable-fence-record-refused')
    # SH proof locks permit nesting under a historical classification adapter;
    # there is no recursive per-UID EX upgrade during effect ownership checks.
    with factory().withdrawal.lock(1002,False):assert gate.inspect(1002,operation,key)=='fenced'
    record(checks,'ownership-compatible-with-classification-shared-proof-lock')
    assert peer_ok() and (PROOFS/'.deny-1002').read_bytes()==barrier
    record(checks,'peer-positive-proof-catalog-and-manager-preserved-before-second-owner')
    # A second *real* negative operation for the peer is deliberate fixture
    # setup for cross-UID collision controls, not incidental collateral damage.
    peer_operation=secrets.token_hex(16);peer_owner=factory();peer_owner.begin(peer_owner.plan(1000,peer_operation),lambda _:True)
    old=snapshot_ledger();expect('OwnershipConflict',lambda:gate.resume(1000,peer_operation,key,lambda _:(_ for _ in ()).throw(AssertionError('prompted'))))
    assert snapshot_ledger()==old and show(1000)['MainPID']==peer_pid
    record(checks,'second-uid-operation-cannot-claim-first-owner',first_uid=1002,second_uid=1000,peer_operation=peer_operation,peer_existing_manager_preserved=True)
    with ledger().lock(1,True):
        expect('Busy',lambda:gate.plan(1002,operation,key));expect('Busy',lambda:gate.plan(1000,peer_operation,key))
    assert lock.stat().st_ino==inode
    record(checks,'one-stable-global-ledger-lock-serializes-both-uids',uids=[1002,1000],lock_inode=inode)
    passed=True
except BaseException as e:error=str(e);raise
finally:
    cleanup=subprocess.run(['/usr/bin/python3',str(BASE/'cleanup.py')],capture_output=True,text=True,timeout=140)
    result=dict(passed=passed and cleanup.returncode==0,checks=checks,error=error,metadata=meta,cleanup_rc=cleanup.returncode,cleanup_stderr=cleanup.stderr,
        full_account_protection=False,all_producer_quiescence=False,live_producer_inhibition_tested=False,production_journal_qualified=False,
        global_monotonic_revision_qualified=False,anti_rollback_qualified=False,power_loss_tested=False,kernel_reboot_tested=False,real_nss_mutations_tested=False,producer_revocation_tested=False)
    (BASE/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':result['passed'],'checks':len(checks),'cleanup_rc':cleanup.returncode}));assert cleanup.returncode==0,cleanup.stderr
