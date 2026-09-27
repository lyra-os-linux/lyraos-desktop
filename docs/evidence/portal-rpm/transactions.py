"""RPM lifecycle on the one disposable VM. Keep the candidate for session tests."""
import hashlib,json,pathlib,subprocess,sys
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert P('/sys/block/vda/serial').read_text().strip()=='lyra-virtualization-'
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
name='xdg-desktop-portal-gnome'
original='/root/portal-original.rpm'
candidate='/root/portal-rpmbuild/RPMS/x86_64/xdg-desktop-portal-gnome-48.0-160100.2.1.lyra1.x86_64.rpm'
assert hashlib.sha256(P(candidate).read_bytes()).hexdigest()=='a4a5e1c0ebf5fa35b125e003190869f7c636c365b579d1109cacbf7ae1a43b30'
report=P('/root/portal-rpm-transactions.json')
rows=json.loads(report.read_text()) if report.exists() else []
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90)
 rows.append(dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr))
 report.write_text(json.dumps(rows,indent=2))
 assert p.returncode==0,rows[-1]
 return p.stdout
for service in ['gdm','user@1002.service','user@1003.service']:
 p=subprocess.run(['systemctl','is-active',service],capture_output=True,text=True)
 assert p.stdout.strip()=='inactive',(service,p.stdout)
assert 'signatures OK' in run(['rpm','-K',original])
assert 'digests OK' in run(['rpm','-K',candidate])
if sys.argv[1]=='prepare':
 assert run(['rpm','-q','--qf','%{VERSION}-%{RELEASE}',name])=='48.0-160100.2.1'
 assert run(['rpm','-V',name])==''
 baseline=hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest()
 P('/root/portal-rpm-baseline.json').write_text(json.dumps(dict(binary_sha256=baseline)))
 # Both packages retain exactly the same file inventory and service scriptlets.
 for option in ['-qlp','--scripts']:
  def query(file):return run(['rpm',option,file] if option=='-qlp' else ['rpm','-qp',option,file])
  assert query(original)==query(candidate),option
 # Real upgrade and rollback, including scriptlets and triggers.
 run(['rpm','-Uvh','--test',candidate]);run(['rpm','-Uvh',candidate]);assert run(['rpm','-V',name])==''
 run(['rpm','-Uvh','--oldpackage',original]);assert run(['rpm','-V',name])==''
 assert hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest()==baseline
 # Fresh installation after dependency-checked removal, in this VM only.
 run(['rpm','-e','--test',name]);run(['rpm','-e',name])
 try:run(['rpm','-ivh',candidate])
 except BaseException:
  run(['rpm','-Uvh','--oldpackage',original]);raise
 assert run(['rpm','-V',name])==''
 expected=dict(nevra=run(['rpm','-q',name]).strip(),rpm_sha256=hashlib.sha256(P(candidate).read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest(),signed=False)
 P('/root/portal-rpm-expected.json').write_text(json.dumps(expected,indent=2))
 print(json.dumps(expected))
elif sys.argv[1]=='restore':
 run(['rpm','-Uvh','--oldpackage',original]);assert run(['rpm','-V',name])==''
 assert run(['rpm','-q','--qf','%{VERSION}-%{RELEASE}',name])=='48.0-160100.2.1'
 assert hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest()==json.loads(P('/root/portal-rpm-baseline.json').read_text())['binary_sha256']
 print('Original signed SUSE RPM restored and verified')
else:raise SystemExit('expected prepare or restore')
