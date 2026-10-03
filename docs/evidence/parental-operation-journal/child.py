"""Actual subprocess exit91 immediately after named durable boundary."""
import sys
exec((__import__('pathlib').Path('/root/operation-journal')/'op-common.py').read_text())
uid=1002;operation,point=sys.argv[1:]
o=factory(point);plan=o.plan(uid,operation);o.begin(plan,lambda row:True)
raise AssertionError('requested crash point did not exit')
