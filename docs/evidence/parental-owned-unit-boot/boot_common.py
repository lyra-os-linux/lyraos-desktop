"""Disposable VM snapshots and read-only live adapter factory for boot checks."""
from fixture import *
from live_common import *
spec=importlib.util.spec_from_file_location('manager_adapters',BASE/'manager_adapters.py')
ma=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ma;spec.loader.exec_module(ma)
WANTS=Path('/etc/systemd/system/multi-user.target.wants')
BOOT_UNITS=(TARGET_UNITS[0],TARGET_UNITS[3],PEER_UNITS[0],PEER_UNITS[2])
def files(directory):
    return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),mode=p.stat().st_mode&0o777,uid=p.stat().st_uid,gid=p.stat().st_gid,nlink=p.stat().st_nlink,inode=p.stat().st_ino) for p in directory.iterdir()}
def persistent():
    return dict(proofs=files(PROOFS),catalog=files(ic.CATALOG),ledger=files(LEDGER),registry=files(DIRECTORY),roles=files(ROLES),
        masks={n:dict(target=os.readlink(MASKS_DIR/n),device=(MASKS_DIR/n).lstat().st_dev,inode=(MASKS_DIR/n).lstat().st_ino) for n in TARGET_UNITS},
        vendor={n:dict(sha256=hashlib.sha256((VENDOR_UNITS/n).read_bytes()).hexdigest(),inode=(VENDOR_UNITS/n).stat().st_ino) for n in TARGET_UNITS+PEER_UNITS},
        wants={n:os.readlink(WANTS/n) for n in BOOT_UNITS},hook_sha256=hashlib.sha256(UNIT.read_bytes()).hexdigest())
def expect(code,action):
    try:action()
    except oc.GateError as e:assert e.code==code,(e.code,code)
    else:raise AssertionError('expected '+code)
def records():
    gate=owned_factory();meta=config()
    return {n:ownership.decode(gate.plan(1002,meta['operation'],('system-units',n)).entry) for n in TARGET_UNITS}
def target():
    meta=config();return oc.Target(1002,meta['operation'],meta['proof_hash'])
def live_adapter(commands,authorizations):
    ma=sys.modules['manager_adapters'];ua=sys.modules['unit_adapter'];meta=config()
    sources={n:bytes.fromhex(v) for n,v in meta['unit_sources'].items()}
    def secure(p,expected):
        s=p.lstat();return stat.S_ISREG(s.st_mode) and s.st_uid==0 and not s.st_mode&0o022 and s.st_nlink==1 and hashlib.sha256(p.read_bytes()).hexdigest()==expected
    classification=ma.Classification(make(),ma.Identity('ordinaryuser',1002,1003,'ordinaryuser'),ic.identity,
        lambda:secure(PAM,meta['fixture_pam_sha256']) and secure(MODULE,meta['fixture_module_sha256']) and run(['getenforce'])['stdout'].strip()=='Enforcing')
    units=tuple(ua.Unit(n,'timer',n[:-6]+'.service') if n.endswith('.timer') else ua.Unit(n,'service') for n in TARGET_UNITS)
    def execute(args):commands.append(args);return run(args,check=False)
    def authorize(t,a,u):unlocked_authority();authorizations.append(a);return True
    return ua.SystemUnits(classification,units,lambda i,u:verify_catalog(i,u,sources),integration.CheckedMasks(owned_factory(),target(),TARGET_UNITS),execute,
        lambda n:unit_show(n)['LoadState']=='masked',lambda u:observe(u,[]),authorize)
