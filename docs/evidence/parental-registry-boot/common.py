"""Shared utilities restricted to the dedicated disposable VM."""
import hashlib,importlib.util,json,os,pwd,subprocess,time
from pathlib import Path
assert os.geteuid()==0
assert {'lyra.parental-selinux-test=1','lyra.parental-identity-test=1'}<=set(Path('/proc/cmdline').read_text().split())
assert Path('/sys/block/vda/serial').read_text().strip()=='lyra-admission-test'
BASE=Path('/root/registry-boot');CONFIG=BASE/'config.json';PAM=Path('/etc/pam.d/systemd-user')
VENDOR=Path('/usr/lib/pam.d/systemd-user');MODULE=Path('/usr/lib64/security/pam_lyra_identity_registry_fixture.so')
DIRECTORY=Path('/var/lib/lyra-parental-test');GUARD=Path('/root/barrier-pam-guard.c');WRITER=Path('/root/barrier-writer.py')
UNIT=Path('/etc/systemd/system/lyra-registry-boot-fixture.service');CONTEXT='lyra_parental_u:lyra_parental_r:lyra_parental_probe_t:s0'
IDENTITY=dict(user='parentaltest',uid=1003,gid=1004,group='parentaltest')
for name,uid,gid in (('parentaltest',1003,1004),('ordinaryuser',1002,1003)):
    account=pwd.getpwnam(name);assert (account.pw_uid,account.pw_gid)==(uid,gid)
spec=importlib.util.spec_from_file_location('writer',WRITER);writer=importlib.util.module_from_spec(spec);spec.loader.exec_module(writer)
def run(args,check=True):
    p=subprocess.run(args,capture_output=True,text=True,timeout=35)
    row=dict(rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
    if check and p.returncode:raise RuntimeError((args,row))
    return row
def boot_id():return Path('/proc/sys/kernel/random/boot_id').read_text().strip()
def show(uid):
    return dict(line.split('=',1) for line in run(['systemctl','show',f'user@{uid}.service','-p','MainPID','-p','ActiveState','-p','ExecMainStatus'])['stdout'].splitlines())
def context(uid):return Path('/proc',show(uid)['MainPID'],'attr/current').read_text().strip('\x00\n ')
def stop(uid):
    run(['systemctl','stop',f'user@{uid}.service']);assert show(uid)['MainPID']=='0'
def uid_processes(uid):
    found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            uids=[int(v) for v in next(line.split()[1:] for line in (p/'status').read_text().splitlines() if line.startswith('Uid:'))]
            if uid in uids:found.append(dict(pid=int(p.name),uids=uids,comm=(p/'comm').read_text().strip()))
        except FileNotFoundError:pass
    return found
def holders():
    ids={(p.stat().st_dev,p.stat().st_ino) for p in DIRECTORY.glob('.lease-*.lock')};found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            for fd in (p/'fd').iterdir():
                try:s=fd.stat()
                except FileNotFoundError:continue
                if (s.st_dev,s.st_ino) in ids:found.append(dict(pid=int(p.name),fd=fd.name,comm=(p/'comm').read_text().strip()))
        except FileNotFoundError:pass
    return found
def wait_state(uid,expected):
    end=time.monotonic()+25
    while time.monotonic()<end:
        state=show(uid)
        if state['ActiveState']==expected:return state
        time.sleep(.1)
    raise AssertionError((uid,expected,show(uid)))
def install_pam(generation):
    text=VENDOR.read_text()+'\n'
    text+='session [success=1 default=ignore] pam_succeed_if.so quiet user != parentaltest uid ne 1003 gid ne 1004\n'
    text+=f'session required pam_lyra_identity_registry_fixture.so account=active|parentaltest|1003|1004|parentaltest|{generation}\n'
    PAM.write_text(text);PAM.chmod(0o644);run(['restorecon',str(PAM)])
def file_state():
    return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=p.stat().st_mode&0o777,uid=p.stat().st_uid) for p in DIRECTORY.iterdir() if p.is_file()}
def config():return json.loads(CONFIG.read_text())
def save(value):CONFIG.write_text(json.dumps(value,indent=2)+'\n');CONFIG.chmod(0o600)
def record(checks,name,**details):
    row=dict(name=name,passed=True,**details);checks.append(row);print(json.dumps(row),flush=True)
def save_result(name,checks,**details):
    row=dict(passed=True,checks=checks,boot_id=boot_id(),full_account_protection=False,**details)
    (BASE/(name+'.json')).write_text(json.dumps(row,indent=2)+'\n')

def drain(uid,name):
    end=time.monotonic()+30
    while time.monotonic()<end:
        known=run(['loginctl','show-user',name],check=False)['rc']==0
        runtime=run(['systemctl','show',f'user-runtime-dir@{uid}.service','-p','ActiveState','--value'])['stdout'].strip()
        if not known and runtime=='inactive' and not uid_processes(uid):return
        time.sleep(.2)
    raise AssertionError(('logind not drained',uid,known,runtime))
