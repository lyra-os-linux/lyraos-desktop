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
target=oc.Target(1002,sys.argv[1],sys.argv[2]);point=sys.argv[3]
assert point in ('origin-synced','intent-synced','request-returned','acceptance-synced')
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
from recovery import retain
from pam import PamExecution
from linux import Linux
from backend import NativeStopBackend
import signal
trace=dict(pid=os.getpid(),point=point,request_entries=0,request_returns=0,authorization_calls=0)
def audit():
    fd=os.open(effect_dir,os.O_RDONLY|os.O_DIRECTORY)
    try:writer.RegistryStore._atomic(fd,'.crash-trace.json',(json.dumps(trace)+'\n').encode())
    finally:os.close(fd)
def abrupt(stage):
    trace['crash_stage']=stage;audit();os._exit(91)
for fd in Path('/proc/self/fd').iterdir():
    try:assert fd.readlink().as_posix()!='anon_inode:[pidfd]'
    except FileNotFoundError:pass
properties=json.loads((BASE/'crash-properties.json').read_text())
ref=origins.capture(unit,properties)
def runtime(name):return {k:v for k,v in read(name).items() if k in ('MainPID','ControlGroup')}
backend=Linux(runtime)
def parent(pin):return int(next(line.split()[1] for line in backend.data(pin,'status').decode().splitlines() if line.startswith('PPid:')))
backend.parent=parent
members=lambda name:tuple(sorted(p['pid'] for p in scoped_processes((name,))))
guarded=PamExecution((sys.modules['unit_adapter'].Unit(unit,'service'),),{unit:ref},backend,sources,fenced,lambda args:(_ for _ in ()).throw(AssertionError('unguarded IPC')),members)
origins.invocation=lambda name:read(name)['InvocationID']
original_atomic=effects.storage.atomic
def atomic(fd,name,data):
    original_atomic(fd,name,data)
    if name==effects.name(unit):
        phase=json.loads(data)['phase']
        if point=='intent-synced' and phase=='intent':abrupt(point)
        if point=='acceptance-synced' and phase=='accepted':abrupt(point)
effects.storage.atomic=atomic
try:
    with retain(guarded,boot_id) as origin:
        origins.seal(origin,properties)
        if point=='origin-synced':abrupt(point)
        hold=Path('/run/lyra-pam-close-hold-test')
        fd=os.open(hold,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o644);os.fsync(fd);os.close(fd)
        signal.pidfd_send_signal(origin.main._pin.descriptor,signal.SIGTERM)
        deadline=time.monotonic()+3
        while not backend.exited(origin.main._pin) or runtime(unit)['MainPID']['data']!=0:
            assert time.monotonic()<deadline;time.sleep(.02)
        assert not backend.exited(origin.helper)
        native=NativeStopBackend(effects,(unit,),{unit:'/system.slice/'+unit},{unit:[origin.main._pin.descriptor,origin.helper.descriptor]},BASE/'unused-sender','never-dropped.service',origin.check)
        class AuditBackend:
            def request(self,name):
                trace['request_entries']+=1;audit()
                reply=native.request(name)
                trace['request_returns']+=1;trace['reply']=reply;audit()
                if point=='request-returned':abrupt(point)
                return reply
            def drained(self,name):return native.drained(name)
        def authorize(request):
            unlocked_authority()
            with effects.storage.lock(1002,True):pass
            trace['authorization_calls']+=1;audit();return True
        origin.recover(effects,AuditBackend(),authorize)
        raise AssertionError('crash point not reached')
finally:
    # os._exit deliberately skips this marker and context-manager cleanup.
    (BASE/'crash-finally-ran').write_text('unexpected normal unwind')
