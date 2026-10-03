"""Disposable persistent D-Bus snapshots and trusted read-only factory."""
from fixture import *
from live_common import *
spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py')
ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
def files(directory):
    return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=p.stat().st_mode&0o777,uid=p.stat().st_uid,gid=p.stat().st_gid,nlink=p.stat().st_nlink,inode=p.stat().st_ino) for p in directory.iterdir()}
def one(p):
    s=p.stat();return dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=s.st_mode&0o777,uid=s.st_uid,gid=s.st_gid,nlink=s.st_nlink,inode=s.st_ino,device=s.st_dev)
def persistent():
    return dict(proofs=files(PROOFS),catalog=files(ic.CATALOG),ledger=files(LEDGER),registry=files(DIRECTORY),roles=files(ROLES),
        retirements={s:one(retired_path(s)) for s in TARGET},active_sources_absent={s:not service_path(s).exists() and not service_path(s).is_symlink() for s in TARGET},
        peer_routes={s:one(service_path(s)) for s in PEERS},vendor={s:one(UNITS/unit_name(s)) for s in SHORTS if systemd(s)},
        binary=one(BINARY),policy=one(POLICY),hook_sha256=hashlib.sha256(UNIT.read_bytes()).hexdigest())
def expect(code,action):
    try:action()
    except oc.GateError as e:assert e.code==code,(e.code,code)
    else:raise AssertionError('expected '+code)
def records():
    gate=owned_factory();meta=config()
    return {s:ownership.decode(gate.plan(1002,meta['operation'],('dbus-activation',PREFIX+s)).entry) for s in TARGET}
def target():
    meta=config();return oc.Target(1002,meta['operation'],meta['proof_hash'])
def broker():
    pid=ushow('dbus.service')['MainPID'];assert int(pid)>0
    return dict(pid=pid,boot_id=boot_id(),stat=Path('/proc',pid,'stat').read_text().split()[21])
def secure_digest(p,h):
    st=p.lstat();return stat.S_ISREG(st.st_mode) and st.st_uid==0 and not st.st_mode&0o022 and st.st_nlink==1 and hashlib.sha256(p.read_bytes()).hexdigest()==h
def live_adapter(effects,authorizations):
    da=sys.modules['dbus_adapter'];meta=config();sources=json.loads(SOURCES.read_text())
    classification=ma.Classification(make(),ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),ic.identity,
        lambda:secure_digest(PAM,meta['fixture_pam_sha256']) and secure_digest(MODULE,meta['fixture_module_sha256']) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    routes=tuple(da.Route(PREFIX+s,hashlib.sha256(sources[str(service_path(s))].encode()).hexdigest(),unit_name(s) if systemd(s) else '') for s in TARGET)
    def reload():effects.append('reload-config');return reload_bus()
    def stop(r):raise AssertionError('boot qualification never revokes stale preboot payload descriptors')
    def authorize(t,a,r):unlocked_authority();authorizations.append(a);return True
    return da.DBusActivation(classification,routes,lambda i,r:catalog(i,r,sources),integration.CheckedRoutes(owned_factory(),target(),routes),reload,
        lambda r:not({x.name for x in r}&activatable()),stop,lambda r:observe(r,[]),authorize)
def blocked_probe(short):
    r=run(['busctl','--system','--timeout=5','call',PREFIX+short,'/org/lyra/ParentalDbusFixture','org.lyra.ParentalDbusFixture','Probe'],check=False)
    assert r['rc'] and any(x in r['stderr'] for x in ('ServiceUnknown','not activatable','not provided by any .service')) and not owner(short),r
    return r
