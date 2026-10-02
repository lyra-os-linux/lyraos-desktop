"""Filesystem refusal controls on a root-private scratch directory, VM only."""
from common import *
from coordinator import GateError
import sys,shutil
spec=importlib.util.spec_from_file_location('unit_adapter',BASE/'unit-adapter.py')
u=importlib.util.module_from_spec(spec);sys.modules[spec.name]=u;spec.loader.exec_module(u)
scratch=BASE/'mask-controls-scratch';assert not scratch.exists();scratch.mkdir(mode=0o700)
checks=[]
def expect(action):
    try:action()
    except GateError as error:assert error.code=='UnsafeMasks'
    else:raise AssertionError('unsafe masks accepted')
try:
    masks=u.Masks(scratch);(scratch/'b.service').write_bytes(b'KEEP ORIGINAL\n')
    expect(lambda:masks.install(('a.service','b.service')))
    assert masks.masked('a.service') and (scratch/'b.service').read_bytes()==b'KEEP ORIGINAL\n'
    record(checks,'partial-mask-failure-keeps-first-mask-and-original-file')
    inode=(scratch/'a.service').lstat().st_ino;assert masks.install(('a.service',)) and (scratch/'a.service').lstat().st_ino==inode
    record(checks,'retry-preserves-existing-mask-inode')
    (scratch/'wrong.service').symlink_to('/some/other/target');expect(lambda:masks.install(('wrong.service',)))
    assert os.readlink(scratch/'wrong.service')=='/some/other/target'
    record(checks,'unexpected-link-never-overwritten')
    os.link(scratch/'a.service',scratch/'duplicate.service',follow_symlinks=False)
    assert (scratch/'a.service').lstat().st_nlink==2;expect(lambda:masks.install(('a.service',)))
    (scratch/'duplicate.service').unlink();assert masks.masked('a.service')
    record(checks,'hard-linked-mask-rejected')
    scratch.chmod(0o770);expect(lambda:masks.masked('a.service'));scratch.chmod(0o700)
    record(checks,'writable-mask-directory-rejected')
    alias=BASE/'mask-controls-alias';assert not alias.exists();alias.symlink_to(scratch)
    try:
        try:u.Masks(alias).masked('a.service')
        except OSError:pass
        else:raise AssertionError('symlink directory followed')
    finally:alias.unlink()
    record(checks,'symlink-mask-directory-rejected')
finally:shutil.rmtree(scratch)
row=dict(passed=True,checks=checks,scratch_removed=not scratch.exists(),enforce=run(['getenforce'])['stdout'].strip(),source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (Path(__file__),BASE/'unit-adapter.py',BASE/'common.py',BASE/'coordinator.py')})
(BASE/'mask-controls.json').write_text(json.dumps(row,indent=2)+'\n');print(json.dumps({'passed':True,'controls':len(checks)}))
