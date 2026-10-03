from owned_common import *
import sys
operation,family,name,point=sys.argv[1:]
owned_factory(point).resume(1002,operation,(family,name),lambda _:True)
raise AssertionError('expected actual child crash91')
