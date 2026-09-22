"""Root-only disposable PAM-session harness; does not authenticate a login."""
import ctypes,json,os,pathlib,pwd,sys
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
user=sys.argv[1];assert user in ('parentaltest','ordinaryuser')
program=sys.argv[2];assert program in ('/opt/lyra-parental-probe/probe','/usr/bin/python3')
pam=ctypes.CDLL('libpam.so.0');selinux=ctypes.CDLL('libselinux.so.1')
P=ctypes.c_void_p;I=ctypes.c_int
CALLBACK=ctypes.CFUNCTYPE(I,I,P,P,P)
@CALLBACK
def reject_conversation(n,msg,resp,data):return 19
class Conv(ctypes.Structure):_fields_=[('conv',CALLBACK),('data',P)]
conv=Conv(reject_conversation,None);handle=P()
pam.pam_start.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.POINTER(Conv),ctypes.POINTER(P)]
for name in ['pam_open_session','pam_close_session','pam_end']:
 getattr(pam,name).argtypes=[P,I];getattr(pam,name).restype=I
selinux.getexeccon.argtypes=[ctypes.POINTER(P)];selinux.freecon.argtypes=[P]
rc=pam.pam_start(b'lyra-parental-probe',user.encode(),ctypes.byref(conv),ctypes.byref(handle));assert rc==0,rc
opened=False
try:
 rc=pam.pam_open_session(handle,0);context=P();getrc=selinux.getexeccon(ctypes.byref(context))
 value=ctypes.string_at(context).decode() if context.value else None
 if context.value:selinux.freecon(context)
 print(json.dumps({'pam_open_rc':rc,'getexeccon_rc':getrc,'selected_context':value,'user':user}),flush=True)
 if rc:sys.exit(70)
 opened=True;account=pwd.getpwnam(user)
 pid=os.fork()
 if pid==0:
  os.setgroups([]);os.setgid(account.pw_gid);os.setuid(account.pw_uid)
  try:os.execv(program,[program,*sys.argv[3:]])
  except OSError as e:print(json.dumps({'exec_errno':e.errno}),flush=True);os._exit(126)
 _,status=os.waitpid(pid,0)
 sys.exit(os.waitstatus_to_exitcode(status))
finally:
 if opened:pam.pam_close_session(handle,0)
 pam.pam_end(handle,rc)
