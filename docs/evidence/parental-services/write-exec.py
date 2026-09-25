import pathlib,subprocess,json,pwd,uuid,hashlib,os
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
u=pwd.getpwnam('parentaltest');b=pathlib.Path('/home/parentaltest/runtime-fixture');b.mkdir(exist_ok=True,mode=0o700);os.chown(b,u.pw_uid,u.pw_gid)
subprocess.run(['chcon','-t','user_tmp_t',str(b)],check=True)
target=b/('generated-'+uuid.uuid4().hex)
rows=[]
def run(name,args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=30);r={'name':name,'rc':p.returncode,'stdout':p.stdout,'stderr':p.stderr};rows.append(r);print(json.dumps(r),flush=True);return r
subprocess.run(['setenforce','1'],check=True)
try:
 r=run('restricted-creates-and-executes',['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','--copy-exec','/usr/bin/true',str(target)])
 assert r['rc']==126 and 'written=' in r['stdout'] and 'user_tmp_t' in r['stdout'] and 'created_exec_errno=13' in r['stdout'],r
 assert target.stat().st_uid==u.pw_uid
 assert hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(pathlib.Path('/usr/bin/true').read_bytes()).digest()
 r=run('same-file-unconfined-control',['runuser','-u','parentaltest','--',str(target)]);assert r['rc']==0,r
 r=run('restricted-executable-map',['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','--map',str(target)]);assert r['rc']==126 and 'mmap_errno=13' in r['stdout'],r
 r=run('restricted-memfd-execution',['python3','/root/lyra-parental-pam-probe.py','parentaltest','/opt/lyra-parental-probe/probe','--memfd','/usr/bin/true']);assert r['rc']==126 and 'lyra_parental_runtime_t' in r['stdout'] and 'memfd_map_errno=13' in r['stdout'] and 'memfd_exec_errno=13' in r['stdout'],r
 run('file-label',['ls','-lZ',str(target)])
finally:
 subprocess.run(['setenforce','0'],check=True)
 pathlib.Path('/root/parental-write-exec-result.json').write_text(json.dumps({'full_account_protection':False,'checks':rows},indent=2)+'\n')
