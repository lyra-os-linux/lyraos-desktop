from bridge import *
import sys,importlib.util
for module,name in (('inventory_fixture','inventory_fixture.py'),('inventory_gate','inventory.py'),('operation_journal','operations.py'),('unit_adapter','unit-adapter.py'),('dbus_adapter','dbus-adapter.py'),('owned_inhibitions','ownership.py'),('owned_live','integration.py')):
    spec=importlib.util.spec_from_file_location(module,BASE/name);loaded=importlib.util.module_from_spec(spec);sys.modules[module]=loaded;spec.loader.exec_module(loaded)
ic=sys.modules['inventory_fixture'];ig=sys.modules['inventory_gate'];ops=sys.modules['operation_journal'];ownership=sys.modules['owned_inhibitions'];integration=sys.modules['owned_live']
LEDGER=Path('/var/lib/lyra-pending-activation-ledger-test')
def factory():return ops.Operations(make(),WithdrawalError,ig.Inventory(ic.CATALOG,ic.identity))
def ledger():return __import__('withdrawal').Withdrawal(LEDGER,writer.RegistryStore._atomic,decode_proof)
def owned_factory():
    meta=config();family=meta['resource_family'];file='unit-adapter.py' if family=='system-units' else 'dbus-adapter.py'
    if family=='system-units':backend=ownership.MaskBackend(sys.modules['unit_adapter'].Masks('/etc/systemd/system'))
    else:
        d=sys.modules['dbus_adapter'];backend=ownership.RouteBackend(d.RetiredRoutes('/usr/share/dbus-1/system-services'),d.Route)
    resources=tuple(ownership.Resource(family,name,digest,backend,lambda:hashlib.sha256((BASE/file).read_bytes()).hexdigest()) for name,digest in meta['resource_routes'])
    return ownership.OwnedInhibitions(factory(),ledger(),resources)
def prepare_bindings(family,routes):
    assert not LEDGER.exists();LEDGER.mkdir(mode=0o700)
    fd=os.open(LEDGER/'.gate-1.lock',os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600);os.fsync(fd);os.close(fd)
    fd=os.open(LEDGER,os.O_RDONLY|os.O_DIRECTORY);os.fsync(fd);os.close(fd)
    ic.create_inventory()
    meta=config();meta.update(resource_family=family,resource_routes=routes);save(meta)
    row=ic.manifest(1002,hashlib.sha256((BASE/'manager_adapters.py').read_bytes()).hexdigest(),hashlib.sha256(GUARD.read_bytes()).hexdigest())
    file='unit-adapter.py' if family=='system-units' else 'dbus-adapter.py'
    row['producers'][family]=dict(state='registered',adapter_digest=hashlib.sha256((BASE/file).read_bytes()).hexdigest(),routes=[dict(id=n,digest=h) for n,h in routes])
    ic.publish(1002,row);ic.publish(1000,ic.manifest(1000,hashlib.sha256((BASE/'manager_adapters.py').read_bytes()).hexdigest(),hashlib.sha256(GUARD.read_bytes()).hexdigest()))
    return row
def ledger_state():return {p.name:dict(sha256=hashlib.sha256(p.read_bytes()).hexdigest(),inode=p.stat().st_ino) for p in LEDGER.iterdir()}
def unlocked_authority():
    # Probe all three actual locks EX during an authorization callback.
    fd=os.open(ic.CATALOG/'.inventory-1002.lock',os.O_RDONLY|os.O_NOFOLLOW)
    try:
        ic.fcntl.flock(fd,ic.fcntl.LOCK_EX|ic.fcntl.LOCK_NB)
        with make().lock(1002,True):
            with ledger().lock(1,True):pass
    finally:os.close(fd)
