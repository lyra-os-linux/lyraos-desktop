from pathlib import Path
exec((Path(__file__).resolve().parent/'op-common.py').read_text())
for module,name in (('unit_adapter','unit-adapter.py'),('dbus_adapter','dbus-adapter.py'),('owned_inhibitions','ownership.py')):
    spec=importlib.util.spec_from_file_location(module,BASE/name);loaded=importlib.util.module_from_spec(spec);sys.modules[module]=loaded;spec.loader.exec_module(loaded)
u=sys.modules['unit_adapter'];d=sys.modules['dbus_adapter'];owned=sys.modules['owned_inhibitions']
SCRATCH=BASE/'filesystem-scratch';LEDGER=SCRATCH/'ledger';MASKS=SCRATCH/'masks';ROUTES=SCRATCH/'routes'
def ledger():return __import__('withdrawal').Withdrawal(LEDGER,writer.RegistryStore._atomic,decode_proof)
def resources():
    units=tuple(owned.Resource('system-units',name,digest,owned.MaskBackend(u.Masks(MASKS)),lambda:hashlib.sha256((BASE/'unit-adapter.py').read_bytes()).hexdigest()) for name,digest in config()['mask_routes'])
    routes=tuple(owned.Resource('dbus-activation',name,digest,owned.RouteBackend(d.RetiredRoutes(ROUTES),d.Route),lambda:hashlib.sha256((BASE/'dbus-adapter.py').read_bytes()).hexdigest()) for name,digest in config()['dbus_routes'])
    return units+routes
def owned_factory(point=None):return owned.OwnedInhibitions(factory(),ledger(),resources(),point)
