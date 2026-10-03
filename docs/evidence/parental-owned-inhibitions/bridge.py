from helper import *
import sys,importlib.util
spec=importlib.util.spec_from_file_location('ordinary_coordinator',BASE/'ordinary-coordinator.py')
oc=importlib.util.module_from_spec(spec);sys.modules[spec.name]=oc;spec.loader.exec_module(oc)
def gate():return oc.OrdinaryCoordinator(make(),WithdrawalError,{})
