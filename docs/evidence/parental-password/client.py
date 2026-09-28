"""VM test client for the native greeter peer protocol; secrets only via stdin."""
import json,sys,os
from gi.repository import Gio,GLib
address,user=sys.argv[1:]
connection=Gio.DBusConnection.new_for_address_sync(address,Gio.DBusConnectionFlags.AUTHENTICATION_CLIENT,None,None)
connection.set_exit_on_close(False)
loop=GLib.MainLoop()
path='/org/gnome/DisplayManager/Session'
verifier='org.gnome.DisplayManager.UserVerifier'
greeter='org.gnome.DisplayManager.Greeter'
def emit(event,**extra):print(json.dumps(dict(event=event,**extra)),flush=True)
def call(interface,method,signature,values):
 def done(conn,result,*_):
  try:conn.call_finish(result);emit('method',method=method)
  except GLib.Error as error:emit('error',method=method,error=str(error));loop.quit()
 connection.call(None,path,interface,method,GLib.Variant(signature,values),None,Gio.DBusCallFlags.NONE,15000,None,done,None)
def signal(conn,sender,object_path,interface,name,parameters,*_):
 emit('signal',interface=interface,name=name)
 if name=='SecretInfoQuery':
  service=parameters.unpack()[0]
  assert service=='gdm-password'
  emit('password-prompt')
  answer=json.loads(sys.stdin.readline())['answer']
  call(verifier,'AnswerQuery','(ss)',(service,answer))
 elif name=='SessionOpened':
  call(greeter,'StartSessionWhenReady','(sb)',('gdm-password',True))
connection.signal_subscribe(None,None,None,path,None,Gio.DBusSignalFlags.NONE,signal,None)
connection.connect('closed',lambda *_:(emit('closed'),loop.quit()))
call(greeter,'SelectSession','(s)',('gnome',))
call(verifier,'BeginVerificationForUser','(ss)',('gdm-password',user))
GLib.timeout_add_seconds(60,lambda:(emit('timeout'),loop.quit(),False)[2])
emit('connected',uid=os.getuid())
loop.run()
