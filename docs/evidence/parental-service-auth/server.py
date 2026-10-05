"""Ephemeral system-bus fixture. Never install as a production service."""
import json,subprocess,sys
from pathlib import Path
import dbus,dbus.service,dbus.mainloop.glib
from gi.repository import GLib
import fixture as f

NAME='org.lyraos.ParentalFixture1'
PATH='/org/lyraos/ParentalFixture1'
ACTION='org.lyraos.parental.fixture.'
mode=sys.argv[1];case=Path(sys.argv[2]);assert case.parent==f.DATA
fixture=f.Fixture(case,create=not case.exists())
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus=dbus.SystemBus(private=True)
loop=GLib.MainLoop()
audit=[]
def save():
 (case/'audit.json').write_text(json.dumps(audit,indent=2)+'\n')
def resolve(sender):
 return int(bus.get_unix_user(str(sender)))
fixture.bridge.planner.resolve_sender=resolve
fixture.bridge.planner.capable=lambda uid,association: uid==1000 and fixture.allow is True

def authorize(sender,payload):
 fixture.authorize(payload) # EX probes; its positive answer is ignored
 action=ACTION+('deny' if mode=='deny' else 'challenge' if mode=='cancel' else 'allow')
 p=subprocess.run(['pkcheck','--action-id',action,'--system-bus-name',str(sender),
                   '--allow-user-interaction'],capture_output=True,text=True,timeout=15)
 audit.append(dict(event='polkit',sender=str(sender),uid=resolve(sender),action=action,
                   returncode=p.returncode,locks_free=fixture.probes[-1]))
 save()
 if p.returncode==0:
  if mode=='revoke':fixture.allow=False
  if mode=='catalog-change':
   row=json.loads((fixture.catalog_dir/'catalog.json').read_text());row['revision']+=1
   with f.exclusive(fixture.catalog_dir/'catalog.lock'):
    f.atomic(fixture.catalog_dir,'catalog.json',f.encode(row))
 return p.returncode==0

def public(fn):
 try:return fn()
 except (f.c.Error,f.co.GateError) as e:
  raise dbus.exceptions.DBusException('operation refused',name=NAME+'.Error.'+e.code)

class Service(dbus.service.Object):
 @dbus.service.method(NAME,in_signature='st',out_signature='s',sender_keyword='sender')
 def Plan(self,association,revision,sender=None):
  audit.append(dict(event='plan',sender=str(sender),uid=resolve(sender)));save()
  return public(lambda:fixture.bridge.plan(str(sender),str(association),int(revision)).identifier)
 @dbus.service.method(NAME,in_signature='s',out_signature='s',sender_keyword='sender')
 def Execute(self,identifier,sender=None):
  audit.append(dict(event='execute',sender=str(sender),uid=resolve(sender)));save()
  return public(lambda:fixture.bridge.execute(str(sender),str(identifier),lambda p:authorize(sender,p)))
 @dbus.service.method(NAME,in_signature='ss',out_signature='s',sender_keyword='sender')
 def Resume(self,association,operation,sender=None):
  audit.append(dict(event='resume',sender=str(sender),uid=resolve(sender)));save()
  return public(lambda:fixture.bridge.resume(str(sender),str(association),str(operation),lambda p:authorize(sender,p)))
 @dbus.service.method(NAME,in_signature='',out_signature='s',sender_keyword='sender')
 def OwnState(self,sender=None):
  uid=resolve(sender)
  audit.append(dict(event='own-state',sender=str(sender),uid=uid));save()
  association='b'*32 if uid==1000 else 'a'*32 if uid==1002 else ''
  return public(lambda:fixture.bridge.inspect_admission(str(sender),association))

name=dbus.service.BusName(NAME,bus=bus,do_not_queue=True)
service=Service(bus,PATH)
(case/'ready').write_text('ready')
try:loop.run()
finally:bus.close()
