"""Native fault injection; only the marked disposable VM is accepted."""
import hashlib, json, os
from pathlib import Path
import signal, subprocess, sys, time
import fixture_recovery as recovery
recovery.guard()
path=Path('/usr/bin/xprop')
created=Path('/tmp/lyra-recovery-fault')
if len(sys.argv)>1:
    assert not created.exists()
    recovery.snapshot([path], [created])
    try:
        recovery.snapshot([path], [created])
    except AssertionError:
        pass
    else:
        raise AssertionError('Pending backup was overwritten')
    path.write_bytes(b'intentionally-invalid-disposable-fixture\n')
    path.chmod(0o600)
    created.write_text('fault-injection')
    if sys.argv[1]=='kill':os.kill(os.getpid(),signal.SIGKILL)
    time.sleep(60)
    raise AssertionError('RuntimeMaxSec did not stop the child')
original=path.read_bytes();info=path.stat();label=os.getxattr(path,'security.selinux')
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
    subprocess.run(['rpm','-V','xprop'],check=True)
    results.append(dict(fault=fault,passed=True,rc=p.returncode,stdout=p.stdout,stderr=p.stderr,
                        restored_sha256=hashlib.sha256(original).hexdigest()))
print(json.dumps(results,indent=2))
