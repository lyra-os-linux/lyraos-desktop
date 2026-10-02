"""Crash-injection worker, only reachable in the marked disposable VM."""
from helper import *
import sys
store=make(sys.argv[1]);plan=store.plan(1002,sys.argv[2]);store.begin(plan,lambda _:True)
raise AssertionError('crash point not reached')
