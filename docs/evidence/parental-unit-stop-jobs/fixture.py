"""Registered disposable VM units and read-only producer observations."""
from state import *
import stat,grp,select
PREFIX='lyra-unit-stop-jobs-'
VENDOR_UNITS=Path('/usr/lib/systemd/system');MASKS_DIR=Path('/etc/systemd/system')
TARGET_UNITS=tuple(PREFIX+'target-'+s for s in ('plain.service','guarded.service','tick.service','tick.timer'))
PEER_UNITS=tuple(PREFIX+'peer-'+s for s in ('plain.service','tick.service','tick.timer'))
UNKNOWN=PREFIX+'target-unknown.service'
ALL_UNITS=TARGET_UNITS+PEER_UNITS+(UNKNOWN,)

def unit_show(name):
    row=dict(line.split('=',1) for line in run(['systemctl','show',name,'-p','Id','-p','Names','-p','MainPID','-p','ActiveState','-p','SubState','-p','LoadState','-p','ExecMainStatus','-p','User','-p','Group','-p','PAMName','-p','KillMode','-p','Transient','-p','ControlGroup','-p','FragmentPath','-p','DropInPaths','-p','Triggers'])['stdout'].splitlines())
    row.setdefault('MainPID','0');return row

def scoped_processes(names):
    groups={unit_show(n)['ControlGroup'] for n in names if n.endswith('.service')}
    groups.discard('');found=[]
    for p in Path('/proc').iterdir():
        if not p.name.isdecimal():continue
        try:
            cgroups=[line.split(':',2)[2] for line in (p/'cgroup').read_text().splitlines()]
            if any(c==g or c.startswith(g+'/') for c in cgroups for g in groups):
                uids=[int(v) for v in next(line.split()[1:] for line in (p/'status').read_text().splitlines() if line.startswith('Uid:'))]
                found.append(dict(pid=int(p.name),uids=uids,cgroups=cgroups,comm=(p/'comm').read_text().strip()))
        except FileNotFoundError:pass
    return found

def wait_active(name,old_pid=None):
    end=time.monotonic()+10
    while time.monotonic()<end:
        row=unit_show(name)
        if row['ActiveState']=='active' and int(row['MainPID'])>0 and (old_pid is None or row['MainPID']!=old_pid):return row
        time.sleep(.1)
    raise AssertionError((name,unit_show(name)))

def create_units():
    assert not any((VENDOR_UNITS/n).exists() or (MASKS_DIR/n).exists() or (MASKS_DIR/n).is_symlink() for n in ALL_UNITS)
    for n in ALL_UNITS:assert not(MASKS_DIR/(n+'.d')).exists() and not(VENDOR_UNITS/(n+'.d')).exists()
    sources={}
    for names,user in ((TARGET_UNITS,'ordinaryuser'),(PEER_UNITS,'installeduser')):
        for name in names:
            if name.endswith('.timer'):
                body=f'[Unit]\nDescription=Lyra disposable registered timer\n[Timer]\nOnActiveSec=300ms\nOnUnitInactiveSec=300ms\nAccuracySec=50ms\nUnit={name[:-6]}.service\n'
            else:
                pam='PAMName=systemd-user\n' if name.endswith('-guarded.service') else ''
                body=f'[Unit]\nDescription=Lyra disposable registered service\n[Service]\nType=exec\nUser={user}\nGroup={user}\nKillMode=control-group\n{pam}ExecStart=/usr/bin/sleep 600\n'
            p=VENDOR_UNITS/name;p.write_text(body);p.chmod(0o644);run(['restorecon',str(p)]);sources[name]=body.encode()
    run(['systemctl','daemon-reload']);return sources

def verify_catalog(identity,units,sources):
    expected={u.name for u in units}
    discovered={p.name for p in VENDOR_UNITS.glob(PREFIX+'target-*') if p.name.endswith(('.service','.timer'))}
    if discovered!=expected:return False
    for u in units:
        p=VENDOR_UNITS/u.name;s=p.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=0 or s.st_mode&0o022 or s.st_nlink!=1 or p.read_bytes()!=sources[u.name]:return False
        if any((d/(u.name+'.d')).exists() for d in (MASKS_DIR,VENDOR_UNITS)):return False
        row=unit_show(u.name)
        if row['Id']!=u.name or set(row['Names'].split())!={u.name} or row['Transient']!='no' or row['DropInPaths']:return False
        if row['LoadState']=='loaded':
            if row['FragmentPath']!=str(p):return False
            if u.kind=='service' and (row['User'],row['Group'],row['PAMName'],row['KillMode'])!=(identity.user,identity.group,'systemd-user' if u.name.endswith('-guarded.service') else '','control-group'):return False
            if u.kind=='timer' and set(row['Triggers'].split())!={u.service}:return False
        elif row['LoadState']!='masked':return False
    account=pwd.getpwnam(identity.user);group=grp.getgrnam(identity.group)
    return (account.pw_uid,account.pw_gid,group.gr_gid)==(identity.uid,identity.gid,identity.gid)

def observe(units,pins):
    names=[u.name for u in units]
    return all(unit_show(n)['MainPID']=='0' and unit_show(n)['ActiveState'] in ('inactive','failed') for n in names) and not scoped_processes(names) and not uid_processes(1002) and all(select.select([pin],[],[],0)[0] for pin in pins)

def remove_units():
    # Original baseline has none of these exact, reserved fixture names.
    run(['systemctl','stop',*[n for n in ALL_UNITS if n.endswith('.timer')]],check=False)
    run(['systemctl','stop',*[n for n in ALL_UNITS if n.endswith('.service')]],check=False)
    for n in ALL_UNITS:
        p=MASKS_DIR/n
        if p.is_symlink():assert os.readlink(p)=='/dev/null' and p.lstat().st_uid==0;p.unlink()
        else:assert not p.exists(),p
        (VENDOR_UNITS/n).unlink(missing_ok=True)
    run(['systemctl','daemon-reload']);run(['systemctl','reset-failed',*ALL_UNITS],check=False)
    assert units_removed()['passed']

def units_removed():
    absent={str(d/n):not(d/n).exists() and not(d/n).is_symlink() for d in (MASKS_DIR,VENDOR_UNITS) for n in ALL_UNITS}
    states={n:unit_show(n) for n in ALL_UNITS}
    return dict(passed=all(absent.values()) and all(v['MainPID']=='0' and v['ActiveState'] in ('inactive','failed') for v in states.values()) and not scoped_processes(ALL_UNITS),absent=absent,units=states,scope_processes=scoped_processes(ALL_UNITS))
