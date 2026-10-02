"""Real root filesystem negative controls in private VM scratch after cleanup."""
from common import *
import shutil,sys
sys.path.insert(0,str(BASE))
import coordinator
spec=importlib.util.spec_from_file_location('dbus_adapter',BASE/'dbus-adapter.py');d=importlib.util.module_from_spec(spec);sys.modules[spec.name]=d;spec.loader.exec_module(d)
assert run(['getenforce'])['stdout'].strip()=='Permissive'
scratch=BASE/'retirement-scratch';assert not scratch.exists();scratch.mkdir(mode=0o700)
checks=[];data=b'[D-BUS Service]\nName=org.lyra.Test\n';route=d.Route('org.lyra.Test',hashlib.sha256(data).hexdigest())
a,b=d.RetiredRoutes.names(route);backend=d.RetiredRoutes(scratch)
def rejected(action):
    try:action()
    except (coordinator.GateError,OSError):return
    raise AssertionError('unsafe operation accepted')
def reset():
    for p in scratch.iterdir():p.unlink()
try:
    (scratch/a).write_bytes(data);inode=(scratch/a).stat().st_ino
    assert backend.retire((route,)) and backend.inspect(route)=='retired' and not(scratch/a).exists() and (scratch/b).stat().st_ino==inode
    assert backend.retire((route,)) and (scratch/b).stat().st_ino==inode
    record(checks,'exclusive-retirement-and-retry-preserve-definition-inode')
    reset();(scratch/a).write_bytes(data);os.link(scratch/a,scratch/b)
    assert backend.inspect(route)=='partial' and backend.retire((route,)) and backend.inspect(route)=='retired'
    record(checks,'two-name-intermediate-resumes-without-recreating-active-source')
    reset();(scratch/a).write_bytes(data);(scratch/b).write_bytes(b'conflicting')
    rejected(lambda:backend.retire((route,)));assert (scratch/a).read_bytes()==data and (scratch/b).read_bytes()==b'conflicting'
    record(checks,'destination-conflict-preserves-source-and-existing-record')
    reset();(scratch/a).write_bytes(data);os.link(scratch/a,scratch/'unexpected-link')
    rejected(lambda:backend.retire((route,)));assert (scratch/a).exists() and not(scratch/b).exists()
    record(checks,'unregistered-hardlink-refused')
    reset();(scratch/a).symlink_to('/etc/passwd');rejected(lambda:backend.retire((route,)));assert (scratch/a).is_symlink() and not(scratch/b).exists()
    record(checks,'definition-symlink-refused-without-reading-target')
    reset();(scratch/a).write_bytes(data);scratch.chmod(0o770);rejected(lambda:backend.retire((route,)));scratch.chmod(0o700)
    record(checks,'group-writable-directory-refused')
    reset();link=BASE/'retirement-scratch-link';assert not link.exists();link.symlink_to(scratch)
    try:rejected(lambda:d.RetiredRoutes(link).inspect(route))
    finally:link.unlink()
    record(checks,'directory-symlink-refused')
    rejected(lambda:d.RetiredRoutes.names(d.Route('../bad','a'*64)))
    record(checks,'filesystem-api-refuses-path-traversal')
    row=dict(passed=True,checks=checks,sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),BASE/'dbus-adapter.py',BASE/'common.py')},full_account_protection=False,power_loss_tested=False)
    (BASE/'retirement-controls.json').write_text(json.dumps(row,indent=2)+'\n')
finally:shutil.rmtree(scratch)
assert not scratch.exists()
