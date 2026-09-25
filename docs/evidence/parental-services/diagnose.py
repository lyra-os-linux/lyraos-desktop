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
 time.sleep(5)
 rows.append(run(['journalctl','--sync']))
 r=run(['journalctl','-k','--since',start,'--no-pager']);r['stdout']='\n'.join(l for l in r['stdout'].splitlines() if 'lyra_parental' in l);rows.append(r)
 rows.append(run(['journalctl','-u','user@1003.service','--since',start,'--no-pager']))
finally:
 subprocess.run(['setenforce','0'],check=True)
 subprocess.run(['systemctl','stop','user@1003.service'],timeout=45,check=False)
 rate.write_text(old);subprocess.run(['semodule','-B'],check=True)
 pathlib.Path('/root/parental-service-diagnostics.json').write_text(json.dumps(rows,indent=2)+'\n')
print(json.dumps(rows,indent=2))
