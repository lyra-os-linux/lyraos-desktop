import pathlib,subprocess,json,datetime,time
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
rate=pathlib.Path('/proc/sys/kernel/printk_ratelimit');old=rate.read_text()
rows=[]
def run(a):
 p=subprocess.run(a,capture_output=True,text=True,timeout=60);return {'argv':a,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr}
try:
 rate.write_text('0\n');r=run(['semodule','-DB']);assert r['rc']==0,r
 subprocess.run(['setenforce','1'],check=True)
 start=datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
 rows.append(run(['systemctl','start','user@1003.service']))
 rows.append(run(['env','HOME=/home/parentaltest','XDG_RUNTIME_DIR=/run/user/1003','DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1003/bus','python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','/opt/lyra-parental-probe/busctl','--timeout=5s','--user','list']))
 rows.append(run(['ps','-eo','uid,label,args']))
 time.sleep(3)
 rows.append(run(['journalctl','--sync']))
 r=run(['journalctl','-k','--since',start,'--no-pager']);r['stdout']='\n'.join(l for l in r['stdout'].splitlines() if 'lyra_parental' in l);rows.append(r)
 rows.append(run(['journalctl','-u','user@1003.service','--since',start,'--no-pager']))
finally:
 subprocess.run(['setenforce','0'],check=True)
 pathlib.Path('/root/parental-broker-diagnostics.json').write_text(json.dumps(rows,indent=2)+'\n')
 try:
  subprocess.run(['systemctl','stop','user@1003.service'],timeout=15,check=False)
 except subprocess.TimeoutExpired:
  subprocess.run(['systemctl','kill','--signal=KILL','user@1003.service'],check=False)
 finally:
  rate.write_text(old);subprocess.run(['semodule','-B'],check=True)
print(json.dumps(rows,indent=2))
