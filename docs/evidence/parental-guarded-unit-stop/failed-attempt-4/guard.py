"""Read-only guarded command backend for the existing SystemUnits adapter.

References originate before owned inhibition. A masked manager definition is
never parsed as the original executable configuration. No ownership repair.
"""
from contextlib import contextmanager, ExitStack
from coordinator import GateError
from reference import Reference
from running import capture

class MaskedSources:
    def __init__(self, references, loaded, fingerprints, fenced):
        self.references = dict(references)
        self.loaded = loaded; self.fingerprints = fingerprints; self.fenced = fenced

    def __call__(self, ref):
        if type(ref) is not Reference or self.references.get(ref.configuration.canonical) != ref:
            raise GateError('InvalidPlan')
        name = ref.configuration.canonical
        if self.fenced(name) is not True: raise GateError('UnverifiedAdmission')
        rows = self.loaded(name)
        specs = {'Id':'s', 'Names':'as', 'LoadState':'s', 'FragmentPath':'s', 'NeedDaemonReload':'b'}
        if type(rows) is not dict or set(rows) != set(specs): raise GateError('UnverifiedUnitProperties')
        for key, sig in specs.items():
            row = rows[key]
            if type(row) is not dict or set(row) != {'type','data'} or row['type'] != sig: raise GateError('UnverifiedUnitProperties')
        values = {k:v['data'] for k,v in rows.items()}
        if any(type(values[k]) is not str for k in ('Id','LoadState','FragmentPath')) or type(values['NeedDaemonReload']) is not bool or type(values['Names']) is not list or any(type(n) is not str for n in values['Names']):
            raise GateError('UnverifiedUnitProperties')
        if values['Id'] != name or name not in values['Names'] or ref.configuration.requested not in values['Names'] or values['LoadState'] != 'masked' or values['FragmentPath'] != '/etc/systemd/system/' + name or values['NeedDaemonReload']:
            raise GateError('UnverifiedAdmission')
        if tuple((p,self.fingerprints(p)) for p,_ in ref.fingerprints) != ref.fingerprints:
            raise GateError('Conflict')
        if self.fenced(name) is not True: raise GateError('UnverifiedAdmission')
        return ref

class GuardedExecution:
    def __init__(self, units, references, backend, revalidate, fences, execute):
        self.units = tuple(units); self.references = dict(references)
        self.backend = backend; self.revalidate = revalidate
        self.fences = fences; self.execute = execute
        services = {u.name for u in self.units if u.kind == 'service'}
        if not services or services != set(self.references) or len({u.name for u in self.units}) != len(self.units):
            raise GateError('UnsupportedProducer')
        if any(type(r) is not Reference or r.configuration.canonical != name for name,r in self.references.items()):
            raise GateError('InvalidPlan')
        self._pins = None; self._done = set()

    def _fences(self):
        if any(self.fences(u.name) is not True for u in self.units): raise GateError('UnverifiedAdmission')

    def check(self):
        if self._pins is None: raise GateError('InvalidPlan')
        self._fences()
        for name, pinned in self._pins.items():
            if name not in self._done:
                pinned.check()
            else:
                if self.revalidate(pinned.reference) != pinned.reference: raise GateError('Conflict')
                if not self.backend.exited(pinned._pin): raise GateError('UnverifiedQuiescence')
                rows = self.backend.runtime(name)
                row = rows.get('MainPID') if type(rows) is dict else None
                if type(row) is not dict or set(row) != {'type','data'} or row['type'] != 'u' or type(row['data']) is not int or row['data'] != 0: raise GateError('UnverifiedQuiescence')
        self._fences()

    @contextmanager
    def batch(self):
        if self._pins is not None: raise GateError('InvalidPlan')
        self._fences()
        with ExitStack() as stack:
            self._pins = {}; self._done = set()
            try:
                for name,ref in self.references.items():
                    self._pins[name] = stack.enter_context(capture(ref,self.backend,self.revalidate))
                self.check()
                yield self
            finally:
                self._pins = None; self._done = set()

    def __call__(self, args):
        if args == ['systemctl','daemon-reload'] and self._pins is None:
            return self.execute(args) # Existing adapter authorizes inhibition.
        if type(args) is not list or len(args) != 3 or args[:2] != ['systemctl','stop'] or args[2] not in {u.name for u in self.units}:
            raise GateError('UnsupportedProducer')
        self.check() # Entire pending batch is checked before each effect.
        result = self.execute(args)
        if type(result) is not dict or type(result.get('rc')) is not int: raise GateError('Busy')
        if result['rc'] == 0: self._done.add(args[2])
        return result
