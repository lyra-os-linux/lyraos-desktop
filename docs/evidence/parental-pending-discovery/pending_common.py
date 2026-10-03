"""Actual root fixture observations; no product discovery/coverage issuer."""
from fixture import *
import signal
REQUESTS=[]
def launch_pending(short):
    assert short in ('TargetUnit','TargetExec') and not owner(short)
    args=['busctl','--system','--timeout=30','call',PREFIX+short,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe']
    client=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True);REQUESTS.append(client)
    end=time.monotonic()+10
    while time.monotonic()<end:
        for item in uid_processes(1002):
            p=Path('/proc',str(item['pid']))
            try:
                if (p/'exe').resolve()!=BINARY or (p/'cmdline').read_bytes().split(b'\0')[:-1]!=[str(BINARY).encode(),(PREFIX+short).encode()]:continue
                state=next(l.split()[1] for l in (p/'status').read_text().splitlines() if l.startswith('State:'))
                if state not in ('T','t'):continue
                cg=(p/'cgroup').read_text().strip();unit=cg.rsplit('/',1)[-1];row=ushow(unit)
                assert cg.startswith('0::/system.slice/') and row['MainPID']==str(item['pid']) and not row['PAMName'] and item['uids']==[1002]*4
                if systemd(short):assert unit==unit_name(short) and row['ActiveState']=='activating'
                else:assert unit.startswith('dbus-') and unit.endswith('.service')
                uid=int(row['User']) if row['User'].isdecimal() else pwd.getpwnam(row['User']).pw_uid;assert uid==1002
                assert client.poll() is None and not owner(short)
                descriptor=dict(short=short,pid=item['pid'],uid=1002,uids=item['uids'],cgroup=cg,unit=unit,unit_state=row)
                path=BASE/'pending.json';saved=json.loads(path.read_text()) if path.exists() else {};saved[short]=descriptor;path.write_text(json.dumps(saved,indent=2)+'\n')
                return descriptor,os.pidfd_open(item['pid']),client
            except FileNotFoundError:continue
        if client.poll() is not None:raise AssertionError(('activation completed before pending observation',client.communicate()))
        time.sleep(.1)
    raise AssertionError(('pending producer not found',short,uid_processes(1002)))
def verify_descriptor(item,pin):
    assert not select.select([pin],[],[],0)[0]
    p=Path('/proc',str(item['pid']));row=ushow(item['unit'])
    assert row['MainPID']==str(item['pid']) and (p/'exe').resolve()==BINARY and (p/'cgroup').read_text().strip()==item['cgroup']
    uids=list(map(int,next(l.split()[1:] for l in (p/'status').read_text().splitlines() if l.startswith('Uid:'))));assert uids==[1002]*4 and not row['PAMName']
    assert (p/'cmdline').read_bytes().split(b'\0')[:-1]==[str(BINARY).encode(),(PREFIX+item['short']).encode()]
def release(item,pin):
    verify_descriptor(item,pin);signal.pidfd_send_signal(pin,signal.SIGCONT)
    end=time.monotonic()+8
    while time.monotonic()<end:
        if owner(item['short']):return
        assert not select.select([pin],[],[],0)[0];time.sleep(.1)
    raise AssertionError('released payload did not acquire its name')
def register_observation(item,pin):
    # Root-selected fixture registration of a verified, pinned pending producer.
    verify_descriptor(item,pin)
    data=json.loads(LIVE.read_text());data[item['short']]=item;LIVE.write_text(json.dumps(data,indent=2)+'\n')
def close_clients():
    for p in REQUESTS:
        if p.poll() is None:p.terminate()
        try:p.communicate(timeout=3)
        except subprocess.TimeoutExpired:p.kill();p.communicate()
