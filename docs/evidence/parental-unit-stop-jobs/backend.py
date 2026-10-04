"""Read-only kernel observations and real IPC for the closed VM fixture.

Unit.Job disappearance alone never establishes a drained producer.
"""
from common import *
import select
from coordinator import GateError
class NativeStopBackend:
    def __init__(self,effects,units,cgroups,pins,sender,drop_unit,fences):
        self.effects=effects;self.units=tuple(units);self.cgroups=dict(cgroups);self.pins=pins
        self.sender=sender;self.drop_unit=drop_unit;self.fences=fences
        self.requests=[];self.starts=[];self.pending=None
    def path(self,unit):
        if unit not in self.units:raise GateError('UnsupportedProducer')
        row=json.loads(run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','LoadUnit','s',unit])['stdout'])
        assert row['type']=='o' and len(row['data'])==1;return row['data'][0]
    def property(self,path,interface,name):
        return json.loads(run(['busctl','--system','--json=short','get-property','org.freedesktop.systemd1',path,'org.freedesktop.systemd1.'+interface,name])['stdout'])
    def populated(self,unit):
        if unit.endswith('.timer'):return 0
        path=self.cgroups[unit]
        assert path=='/system.slice/'+unit
        cgroup=Path('/sys/fs/cgroup'+path)
        try:
            row=dict(line.split() for line in (cgroup/'cgroup.events').read_text().splitlines())
            assert row['populated'] in ('0','1');return int(row['populated'])
        except FileNotFoundError:
            if cgroup.exists():raise
            return 0
    def drained(self,unit):
        path=self.path(unit)
        active=self.property(path,'Unit','ActiveState');job=self.property(path,'Unit','Job')
        if active['type']!='s' or active['data'] not in ('inactive','failed') or job!={'type':'(uo)','data':[0,'/']}:return False
        if unit.endswith('.service'):
            if self.property(path,'Service','MainPID')!={'type':'u','data':0} or self.populated(unit)!=0:return False
            if not all(select.select([p],[],[],0)[0] for p in self.pins[unit]):return False
        return True
    def request(self,unit):
        assert self.fences() is True
        assert self.effects.read(unit)['phase']=='intent'
        # The separate effect EX lock is free during IPC, despite the original
        # adapter retaining its classification SH lease.
        with self.effects.storage.lock(1002,True):pass
        for name in self.units:
            r=run(['systemctl','start',name],check=False)
            assert r['rc']!=0 and 'masked' in r['stderr'].lower()
            self.starts.append(dict(unit=name,rc=r['rc'],stderr=r['stderr']))
        self.requests.append(unit)
        if unit==self.drop_unit:
            sender=run([str(self.sender),unit]);assert sender['stdout'].strip()=='request-flushed-reply-unread-connection-closed'
            path=self.path(unit)
            self.pending=dict(active=self.property(path,'Unit','ActiveState'),job=self.property(path,'Unit','Job'),populated=self.populated(unit),drained=self.drained(unit),sender=sender)
            return None
        return json.loads(run(['busctl','--system','--json=short','call','org.freedesktop.systemd1','/org/freedesktop/systemd1','org.freedesktop.systemd1.Manager','StopUnit','ss',unit,'fail'])['stdout'])
