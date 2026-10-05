"""Fixed Unix argv for the isolated fixture; not a product service adapter."""
import grp,subprocess
import fixture as f

def members(user):return sorted(g.gr_name for g in grp.getgrall() if user in g.gr_mem)

def apply(fixture,params,method,account,values,audit,save):
 assert account.identity.uid==1002 and account.identity.user=='ordinaryuser'
 identity=f.identify(1002)
 args=params.command(f.c,method,account,values)
 assert args[0] in ('/usr/sbin/usermod','/usr/bin/gpasswd')
 held=[]
 for lock in (fixture.catalog_dir/'catalog.lock',fixture.inventory_dir/'.inventory-1002.lock',fixture.ledger/'.gate-1002.lock'):
  try:
   with f.exclusive(lock):pass
  except BlockingIOError:held.append(lock.name)
  else:raise AssertionError('missing lease '+lock.name)
 if method=='SetAdmin' and ('wheel' in members('ordinaryuser'))==values.is_admin:
  audit.append(dict(event='noop',method=method,is_admin=values.is_admin,locks_held=held));save();return
 row=subprocess.run(args,capture_output=True,text=True,timeout=10)
 audit.append(dict(event='unix',argv=list(args),returncode=row.returncode,locks_held=held));save()
 assert row.returncode==0,('Unix command failed',row.returncode)
 assert f.identify(1002)==identity
