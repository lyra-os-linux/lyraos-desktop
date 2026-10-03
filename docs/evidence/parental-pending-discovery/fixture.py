"""Reserved fixture names only. Shared broker is never restarted or stopped."""
from state import *
import grp,select,stat,shlex
PREFIX='org.lyra.PendingDiscovery.'
SHORTS=('TargetUnit','TargetExec','TargetColdUnit','TargetColdExec','PeerUnit','PeerExec')
TARGET=SHORTS[:4];PEERS=SHORTS[4:]
SERVICES=Path('/usr/share/dbus-1/system-services');UNITS=Path('/run/systemd/system')
BINARY=Path('/usr/bin/lyra-discovery-dbus-fixture');POLICY=Path('/etc/dbus-1/system.d/lyra-discovery-dbus-fixture.conf')
LIVE=BASE/'live.json';SOURCES=BASE/'sources.json'
def unit_name(short):return 'lyra-discovery-dbus-'+short.lower()+'.service'
def service_path(short):return SERVICES/(PREFIX+short+'.service')
def retired_path(short):return SERVICES/('.lyra-withdrawn-'+PREFIX+short)
def systemd(short):return short.endswith('Unit')
def secure(path,expected):
    s=path.lstat();return stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_nlink==1 and path.read_bytes()==expected

def ushow(name):
    d=dict(line.split('=',1) for line in run(['systemctl','show',name,'-p','MainPID','-p','ActiveState','-p','LoadState','-p','User','-p','PAMName','-p','ControlGroup','-p','FragmentPath','-p','DropInPaths'])['stdout'].splitlines());d.setdefault('MainPID','0');return d

def reload_bus():
    run(['systemctl','daemon-reload'])
    return run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ReloadConfig'],check=False)['rc']==0

def activatable():
    r=run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','ListActivatableNames'])
    parts=shlex.split(r['stdout']);assert parts[0]=='as' and int(parts[1])==len(parts)-2
    return set(parts[2:])
def owner(short):
    r=run(['busctl','--system','call','org.freedesktop.DBus','/org/freedesktop/DBus','org.freedesktop.DBus','NameHasOwner','s',PREFIX+short])
    assert r['stdout'].strip() in ('b true','b false');return r['stdout'].strip()=='b true'
def probe(short):
    r=run(['busctl','--system','--timeout=5','call',PREFIX+short,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'])
    sig,uid,pid=r['stdout'].split();uid=int(uid);pid=int(pid);assert sig=='uu' and uid==(1002 if short in TARGET else 1000)
    p=Path('/proc',str(pid));uids=list(map(int,next(l.split()[1:] for l in (p/'status').read_text().splitlines() if l.startswith('Uid:'))))
    assert uids==[uid]*4 and (p/'exe').resolve()==BINARY
    cg=(p/'cgroup').read_text().strip();assert cg.startswith('0::/system.slice/')
    unit=cg.rsplit('/',1)[-1];assert unit==unit_name(short) if systemd(short) else unit.startswith('dbus-') and unit.endswith('.service')
    row=ushow(unit);assert row['MainPID']==str(pid) and not row['PAMName']
    unituid=int(row['User']) if row['User'].isdecimal() else pwd.getpwnam(row['User']).pw_uid;assert unituid==uid
    item=dict(short=short,pid=pid,uid=uid,uids=uids,cgroup=cg,unit=unit,unit_state=row)
    data=json.loads(LIVE.read_text()) if LIVE.exists() else {};data[short]=item;LIVE.write_text(json.dumps(data,indent=2)+'\n');return item

def create_routes():
    assert not any(p.exists() or p.is_symlink() for p in (BINARY,POLICY,*[service_path(s) for s in SHORTS],*[retired_path(s) for s in SHORTS],*[UNITS/unit_name(s) for s in SHORTS]))
    run(['gcc','-Wall','-Wextra','-Werror','-O2',str(BASE/'service.c'),'-o',str(BINARY),'-lsystemd']);run(['restorecon',str(BINARY)])
    sources={}
    for short in SHORTS:
        name=PREFIX+short;user='ordinaryuser' if short in TARGET else 'installeduser'
        text=f'[D-BUS Service]\nName={name}\nUser={user}\nExec={BINARY} {name}\n'
        if systemd(short):
            text+=f'SystemdService={unit_name(short)}\n'
            p=UNITS/unit_name(short);p.write_text(f'[Service]\nType=dbus\nBusName={name}\nUser={user}\nKillMode=control-group\nExecStart={BINARY} {name}\n');p.chmod(0o644);sources[str(p)]=p.read_text();run(['restorecon',str(p)])
        p=service_path(short);p.write_text(text);p.chmod(0o644);sources[str(p)]=text;run(['restorecon',str(p)])
    policy='<busconfig>\n'
    for user,shorts in (('ordinaryuser',TARGET),('installeduser',PEERS)):
        policy+=f'<policy user="{user}">\n'+''.join(f'<allow own="{PREFIX+s}"/>\n' for s in shorts)+'</policy>\n'
    policy+='<policy user="root">\n'+''.join(f'<allow send_destination="{PREFIX+s}"/>\n' for s in SHORTS)+'</policy>\n</busconfig>\n'
    POLICY.write_text(policy);POLICY.chmod(0o644);run(['restorecon',str(POLICY)])
    sources[str(POLICY)]=policy;sources[str(BINARY)]=hashlib.sha256(BINARY.read_bytes()).hexdigest();SOURCES.write_text(json.dumps(sources,indent=2)+'\n');LIVE.write_text('{}\n');assert reload_bus();return sources

def catalog(identity,routes,sources):
    expected={PREFIX+s for s in TARGET}
    found={p.name[:-8] for p in SERVICES.glob(PREFIX+'Target*.service')}
    retired={p.name.removeprefix('.lyra-withdrawn-') for p in SERVICES.glob('.lyra-withdrawn-'+PREFIX+'Target*')}
    if found|retired!=expected or {r.name for r in routes}!=expected:return False
    if not secure(POLICY,sources[str(POLICY)].encode()) or hashlib.sha256(BINARY.read_bytes()).hexdigest()!=sources[str(BINARY)]:return False
    for short in TARGET:
        if systemd(short):
            p=UNITS/unit_name(short)
            if not secure(p,sources[str(p)].encode()):return False
            row=ushow(p.name)
            if row['FragmentPath']!=str(p) or row['DropInPaths'] or row['User']!=identity.user or row['PAMName']:return False
    a=pwd.getpwnam(identity.user);g=grp.getgrnam(identity.group)
    return (a.pw_uid,a.pw_gid,g.gr_gid)==(identity.uid,identity.gid,identity.gid)

def stop_payloads(routes):
    live=json.loads(LIVE.read_text());names=[r.unit for r in routes if r.unit]
    for short in TARGET:
        if short in live:
            item=live[short];unit=item['unit'];row=ushow(unit)
            if row['MainPID']!='0':
                # Bind every stop to the trusted live payload, UID and cgroup.
                p=Path('/proc',row['MainPID'])
                if row['MainPID']!=str(item['pid']) or (p/'exe').resolve()!=BINARY or (p/'cgroup').read_text().strip()!=item['cgroup']:return False
            if unit not in names:names.append(unit)
    for name in names:
        r=run(['systemctl','stop',name],check=False)
        if r['rc'] and ushow(name)['LoadState']!='not-found':return False
    return True

def observe(routes,pins):
    live=json.loads(LIVE.read_text());names={r.unit for r in routes if r.unit}|{live[s]['unit'] for s in TARGET if s in live}
    return all(not owner(s) for s in TARGET) and all(ushow(n)['MainPID']=='0' for n in names) and not uid_processes(1002) and all(select.select([p],[],[],0)[0] for p in pins)

def remove_routes():
    # Only originally absent reserved fixture files are removed.
    for s in SHORTS:service_path(s).unlink(missing_ok=True);retired_path(s).unlink(missing_ok=True)
    if POLICY.exists():POLICY.unlink()
    assert reload_bus()
    live=json.loads(LIVE.read_text()) if LIVE.exists() else {}
    pending=json.loads((BASE/'pending.json').read_text()) if (BASE/'pending.json').exists() else {}
    live.update(pending)
    for name in {unit_name(s) for s in SHORTS if systemd(s)}|{r['unit'] for r in live.values()}:run(['systemctl','stop',name],check=False)
    for s in SHORTS:(UNITS/unit_name(s)).unlink(missing_ok=True)
    BINARY.unlink(missing_ok=True);assert reload_bus()

def restored_routes():
    paths=(BINARY,POLICY,*[service_path(s) for s in SHORTS],*[retired_path(s) for s in SHORTS],*[UNITS/unit_name(s) for s in SHORTS])
    meta=config();pid=ushow('dbus.service')['MainPID']
    absent={str(p):not p.exists() and not p.is_symlink() for p in paths};owners={s:owner(s) for s in SHORTS}
    return dict(passed=all(absent.values()) and not any(owners.values()) and not({PREFIX+s for s in SHORTS}&activatable()) and pid==meta['broker_pid'],absent=absent,owners=owners,broker_pid=pid)
