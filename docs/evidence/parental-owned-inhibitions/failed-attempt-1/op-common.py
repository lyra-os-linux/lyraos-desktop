"""Dedicated guest factory, admission-withdrawal only, no producer coverage claim."""
from bridge import *
from fixture import *
spec=importlib.util.spec_from_file_location('inventory_gate',BASE/'inventory.py');ig=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ig;spec.loader.exec_module(ig)
spec=importlib.util.spec_from_file_location('operation_journal',BASE/'operations.py');ops=importlib.util.module_from_spec(spec);sys.modules[spec.name]=ops;spec.loader.exec_module(ops)
def factory(point=None):return ops.Operations(make(point),WithdrawalError,ig.Inventory(CATALOG,identity),point)
