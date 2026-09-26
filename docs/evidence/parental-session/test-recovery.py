"""Native fault injection; only the marked disposable VM is accepted."""
import hashlib, json, os
from pathlib import Path
import signal, subprocess, sys, time
import fixture_recovery as recovery
recovery.guard()
path=Path('/usr/bin/xprop')
created=Path('/tmp/lyra-recovery-fault')
cache=Path('/home/parentaltest/.cache/fontconfig')
cache_new=cache/'lyra-fault-cache'
cache_original=cache/'CACHEDIR.TAG'
wp=Path('/home/parentaltest/.local/state/wireplumber')
db=Path('/home/parentaltest/.local/share/flatpak/db')
data_dirs=[wp,db]
search_cache=Path('/home/parentaltest/.cache/tracker3')
external=Path('/tmp/lyra-recovery-preserved-target')
if len(sys.argv)>1:
    assert not created.exists()
    recovery.snapshot([path], [created], cache_directory=cache,data_directories=data_dirs,generated_trees=[search_cache])
    try:
        recovery.snapshot([path], [created], cache_directory=cache,data_directories=data_dirs)
    except AssertionError:
        pass
    else:
        raise AssertionError('Pending backup was overwritten')
    path.write_bytes(b'intentionally-invalid-disposable-fixture\n')
    path.chmod(0o600)
    created.write_text('fault-injection')
    (search_cache/'files/errors').mkdir(parents=True)
    (search_cache/'files/metadata.db').write_text('generated search data')
    (search_cache/'files/external-link').symlink_to(external)
    cache_new.write_text('new disposable cache data')
    cache_original.write_text('mutated original cache data')
    cache.chmod(0o700)
    for directory in data_dirs:
        directory.mkdir(parents=True,exist_ok=True)
        for item in directory.iterdir():
            assert item.is_file() and not item.is_symlink()
            item.write_text('mutated existing portal data')
        (directory/'lyra-fault-new').write_text('new session data')
        directory.chmod(0o700)
    if sys.argv[1]=='kill':os.kill(os.getpid(),signal.SIGKILL)
    time.sleep(60)
    raise AssertionError('RuntimeMaxSec did not stop the child')
original=path.read_bytes();info=path.stat();label=os.getxattr(path,'security.selinux')
assert not search_cache.exists() and not external.exists()
external.write_text('outside generated tree: preserve')
cache_bytes=cache_original.read_bytes();cache_info=cache.stat();cache_label=os.getxattr(cache,'security.selinux');cache_names={p.name for p in cache.iterdir()}
original_data={}
for directory in data_dirs:
    original_data[str(directory)]=None if not directory.exists() else dict(
        files={p.name:p.read_bytes() for p in directory.iterdir()},
        mode=directory.stat().st_mode,mtime=directory.stat().st_mtime_ns,
        label=os.getxattr(directory,'security.selinux'))
results=[]
for fault in ['kill','timeout']:
    command=['systemd-run','--unit=lyra-recovery-'+fault,'--wait','--pipe','--collect',
             '-p','RuntimeMaxSec=3','-p','TimeoutStopSec=180',
             '-p','ExecStopPost=/usr/bin/python3 /root/fixture_recovery.py',
             '/usr/bin/python3',__file__,fault]
    p=subprocess.run(command,capture_output=True,text=True,timeout=220)
    assert p.returncode!=0,(fault,p.stdout,p.stderr)
    assert path.read_bytes()==original and path.stat().st_mode==info.st_mode
    assert path.stat().st_mtime_ns==info.st_mtime_ns
    assert os.getxattr(path,'security.selinux')==label
    assert not created.exists() and not recovery.ACTIVE.exists()
    assert not search_cache.exists() and external.read_text()=='outside generated tree: preserve'
    assert not cache_new.exists() and cache_original.read_bytes()==cache_bytes
    assert cache.stat().st_mode==cache_info.st_mode and cache.stat().st_mtime_ns==cache_info.st_mtime_ns
    assert os.getxattr(cache,'security.selinux')==cache_label
    assert {p.name for p in cache.iterdir()}==cache_names
    for directory in data_dirs:
        saved=original_data[str(directory)]
        if saved is None:
            assert not directory.exists()
        else:
            assert {p.name:p.read_bytes() for p in directory.iterdir()}==saved['files']
            assert directory.stat().st_mode==saved['mode']
            assert directory.stat().st_mtime_ns==saved['mtime']
            assert os.getxattr(directory,'security.selinux')==saved['label']
    subprocess.run(['rpm','-V','xprop'],check=True)
    results.append(dict(fault=fault,passed=True,rc=p.returncode,stdout=p.stdout,stderr=p.stderr,
                        restored_sha256=hashlib.sha256(original).hexdigest()))
external.unlink()
print(json.dumps(results,indent=2))
