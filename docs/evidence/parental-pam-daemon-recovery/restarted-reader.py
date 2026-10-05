"""Fresh experimental consumer: root fixture only, no inherited pidfds or IPC."""
import sys
sys.path.insert(0,'/root/unit-stop-jobs')
from bridge import *
from fixture import *
from live_common import *
from effects import Effects
from restart import Origins,Restarted
from guard import MaskedSources
from cold import SPECS
import support as typed

unit=TARGET_UNITS[1]
target=oc.Target(1002,sys.argv[1],sys.argv[2]);allowed=sys.argv[3]=='allow'
effect_dir=Path('/var/lib/lyra-unit-stop-effects-test')
effects=Effects(factory(),Withdrawal(effect_dir,writer.RegistryStore._atomic,decode_proof),target,dict(config()['resource_routes']),boot_id)
origins=Origins(effects,typed.user,typed.group,typed.fingerprint,lambda p:typed.file_data(p,8192)[0])
masks=integration.CheckedMasks(owned_factory(),target,(unit,))
def fenced(name):return masks.masked(name) is True and unit_show(name)['LoadState']=='masked'
def loaded(name):return {k:v for k,v in typed.properties(name).items() if k in ('Id','Names','LoadState','FragmentPath','NeedDaemonReload')}
def sources(ref):return MaskedSources({unit:ref},loaded,typed.fingerprint,fenced)(ref)
def read(name):
    path=json.loads(typed.run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','LoadUnit','s',name]))['data'][0]
    return {n:json.loads(typed.run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',path,'org.freedesktop.systemd1.'+('Service' if n in ('MainPID','ControlGroup') else 'Unit'),n])) for n in SPECS}
def empty(name):
    path=Path('/sys/fs/cgroup/system.slice',name)
    try:
        populated=dict(line.split() for line in (path/'cgroup.events').read_text().splitlines())['populated']
        assert populated in ('0','1');return populated=='0'
    except FileNotFoundError:
        if path.exists():raise
        return True
calls=[]
def authorize(request):
    unlocked_authority()
    with effects.storage.lock(1002,True):pass
    assert request==dict(unit=unit,uid=1002,operation=target.operation,action='reconcile-cold-pam-unit')
    calls.append(request);return allowed
pidfds=[]
for fd in Path('/proc/self/fd').iterdir():
    try:
        if fd.readlink().as_posix()=='anon_inode:[pidfd]':pidfds.append(fd.name)
    except FileNotFoundError:pass
assert not pidfds
before=effects.read(unit)
try:
    result=Restarted(origins,read,empty,sources).reconcile(unit,authorize)
    outcome='reconciled';code=None
except oc.GateError as error:
    result=None;outcome='blocked';code=error.code
print(json.dumps(dict(pid=os.getpid(),inherited_pidfds=pidfds,outcome=outcome,code=code,authorization_calls=calls,before=before,after=effects.read(unit),result=result,empty=empty(unit),properties=read(unit),ipc_requests=[])))
