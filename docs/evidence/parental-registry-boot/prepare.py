"""Persist an interrupted transaction while a native linger manager is live."""
from common import *
import secrets
checks=[]
assert run(['getenforce'])['stdout'].strip()=='Permissive'
assert not DIRECTORY.exists() and not MODULE.exists() and not UNIT.exists() and not CONFIG.exists()
assert all(show(uid)['MainPID']=='0' and not uid_processes(uid) for uid in (1002,1003))
assert all(not Path('/var/lib/systemd/linger',n).exists() for n in ('parentaltest','ordinaryuser'))
assert not run(['loginctl','list-sessions','--no-legend'])['stdout'].strip()
for uid,name in ((1003,'parentaltest'),(1002,'ordinaryuser')):drain(uid,name)
BASE.mkdir(mode=0o700,exist_ok=True)
original=PAM.read_bytes();(BASE/'original-pam').write_bytes(original)
meta=dict(original_pam_sha256=hashlib.sha256(original).hexdigest(),original_pam_mode=PAM.stat().st_mode&0o777,
    vendor_sha256=hashlib.sha256(VENDOR.read_bytes()).hexdigest(),
    account_sha256={p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in ('/etc/passwd','/etc/group')},
    source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (GUARD,WRITER,Path(__file__),BASE/'common.py',BASE/'recover-at-boot.py')},
    fault=False,initial_boot_id=boot_id())
save(meta)
run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2',str(GUARD),'-o',str(MODULE),'-lpam','-lselinux']);MODULE.chmod(0o755);run(['restorecon',str(MODULE)])
DIRECTORY.mkdir(mode=0o700);run(['restorecon',str(DIRECTORY)])
store=writer.RegistryStore(DIRECTORY);a,b=secrets.token_hex(16),secrets.token_hex(16)
store.seed([dict(state='active',**IDENTITY,generation=a)]);install_pam(a);run(['setenforce','1'])
run(['systemctl','start','user@1003.service']);assert context(1003)==CONTEXT
record(checks,'initial-generation-native-manager-admitted',unit=show(1003),context=context(1003))
try:store.begin(a)
except writer.StoreError as error:assert str(error).startswith('busy:');busy=str(error)
else:raise AssertionError('manager did not keep lease')
record(checks,'initial-live-manager-keeps-durable-busy-barrier',error=busy,holders=holders())
stop(1003);drain(1003,'parentaltest');assert not holders()
store.begin(a);store.tombstone(a)
publication=run(['/usr/bin/python3',str(WRITER),'publish',str(DIRECTORY),a,'--record-json',json.dumps(dict(state='active',**IDENTITY,generation=b)),'--crash-at','barrier-new-removed'],check=False)
assert publication['rc']==writer.CRASH_EXIT,publication
record(checks,'explicit-generation-publication-before-reboot',old_generation=a,new_generation=b,snapshot=store.snapshot(),publication=publication)
install_pam(b)
for user,uid in (('parentaltest',1003),('ordinaryuser',1002)):
    run(['loginctl','enable-linger',user]);wait_state(uid,'active')
assert context(1003)==CONTEXT and ':unconfined_t:' in context(1002)
record(checks,'both-native-linger-managers-active-before-interruption',supervised=show(1003),ordinary=show(1002))
# The writer exits immediately after fsync of the new barrier, before its journal.
child=run(['/usr/bin/python3',str(WRITER),'begin',str(DIRECTORY),b,'--crash-at','barrier-old-published'],check=False)
assert child['rc']==writer.CRASH_EXIT,child
rows,journals=store.snapshot();assert next(r for r in rows if r['generation']==b)['state']=='active'
assert b not in journals and journals[a]['phase']=='committed'
assert (DIRECTORY/('.barrier-'+b)).exists() and any(h['comm']=='(sd-pam)' for h in holders())
record(checks,'interruption-leaves-active-row-new-barrier-and-older-committed-journal',command=child,snapshot=[rows,journals],holders=holders())
meta.update(generation_a=a,generation_b=b,before_reboot_files=file_state());save(meta)
UNIT.write_text('[Unit]\nDescription=Disposable registry recovery qualification\nAfter=local-fs.target\nBefore=systemd-logind.service user@1003.service user@1002.service\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /root/registry-boot/recover-at-boot.py\n[Install]\nWantedBy=multi-user.target\n')
run(['restorecon',str(UNIT)]);run(['systemctl','daemon-reload']);run(['systemctl','enable',UNIT.name])
record(checks,'fixture-recovery-ordered-before-logind-with-two-linger-markers',unit=UNIT.read_text())
save_result('prepared',checks,metadata=meta)
