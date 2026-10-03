"""Marked VM backend: actual /proc, pidfds and verified systemd stop."""
from fixture import *
from discovery import Observation,Discovery
from coordinator import GateError
class ProcInventory:
    def __init__(self,sources,guard):
        self.sources=sources;self.guard=guard;self.events=[];self.inject=lambda:None;self.lose_response=False
        self.binary_stamp=self.binary()
    def binary(self):
        s=BINARY.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or s.st_nlink!=1 or s.st_size>16*1024*1024:raise GateError('UnverifiedProducerCatalog')
        h=hashlib.sha256(BINARY.read_bytes()).hexdigest()
        if h!=self.sources[str(BINARY)]:raise GateError('UnverifiedProducerCatalog')
        return s.st_dev,s.st_ino,h
    def version(self):
        if self.guard() is not True or self.binary()!=self.binary_stamp:raise GateError('UnverifiedAdmission')
        return self.binary_stamp
    def pids(self,uid):return [p['pid'] for p in uid_processes(uid)]
    def pin(self,pid):return os.pidfd_open(pid)
    def exited(self,pin):return bool(select.select([pin],[],[],0)[0])
    def close(self,pin):os.close(pin)
    def read(self,pid):
        p=Path('/proc',str(pid));data=(p/'cmdline').read_bytes()
        if len(data)>4096:raise GateError('UnsupportedProducer')
        argv=tuple(x.decode() for x in data.split(b'\0')[:-1])
        if len(argv)!=2 or argv[0]!=str(BINARY) or argv[1] not in {PREFIX+s for s in TARGET} or (p/'exe').resolve()!=BINARY:raise GateError('UnsupportedProducer')
        executable=(p/'exe').stat()
        if (executable.st_dev,executable.st_ino)!=self.binary_stamp[:2]:raise GateError('UnsupportedProducer')
        short=argv[1].removeprefix(PREFIX);cg=(p/'cgroup').read_text().strip();unit=cg.rsplit('/',1)[-1];row=ushow(unit)
        if row['MainPID']!=str(pid) or row['PAMName'] or row['ControlGroup']!=cg.removeprefix('0::') or row['DropInPaths']:raise GateError('UnsupportedProducer')
        uid=int(row['User']) if row['User'].isdecimal() else pwd.getpwnam(row['User']).pw_uid
        if uid!=1002:raise GateError('UnsupportedProducer')
        if systemd(short):
            path=UNITS/unit_name(short)
            if unit!=path.name or row['FragmentPath']!=str(path) or not secure(path,self.sources[str(path)].encode()):raise GateError('UnsupportedProducer')
        else:
            if not unit.startswith('dbus-') or '-'+argv[1]+'@' not in unit or row['FragmentPath']!='/run/systemd/transient/'+unit:raise GateError('UnsupportedProducer')
            s=Path(row['FragmentPath']).lstat()
            if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or s.st_nlink!=1:raise GateError('UnsupportedProducer')
        uids=tuple(map(int,next(l.split()[1:] for l in (p/'status').read_text().splitlines() if l.startswith('Uid:'))))
        ticks=int((p/'stat').read_text().rsplit(')',1)[1].split()[19])
        return Observation(pid,1002,uids,argv[1],unit,cg,self.binary_stamp,argv,ticks)
    def stop(self,row):
        result=run(['systemctl','stop',row.unit],check=False);self.events.append(dict(unit=row.unit,pid=row.pid,result=result))
        if result['rc']:return False
        if self.lose_response:return False # Real stop executed, outcome withheld from caller.
        return True
    def after_batch(self):self.inject()
