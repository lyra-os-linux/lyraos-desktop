"""Install/upgrade/restore the exact signed staging RPMs in the disposable VM."""
import hashlib,json,pathlib,subprocess,sys
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
assert P('/sys/block/vda/serial').read_text().strip()=='lyra-virtualization-'
assert not P('/root/lyra-xwayland-recovery/active.json').exists()
name='xdg-desktop-portal-gnome';lang=name+'-lang'
original='/root/portal-original.rpm';candidate='/root/portal-staging.rpm';translations='/root/portal-staging-lang.rpm'
for file,digest in [(candidate,'9e7f6622e12cc8c343f772b5900d4ca7e4be01c9a20ef9477cf24373e55b1670'),(translations,'ba84d6486f3b5907c86e0a38e17d93e939e0dbb674cd3ea4754deac256f50a28')]:
 assert hashlib.sha256(P(file).read_bytes()).hexdigest()==digest
report=P('/root/portal-staging-transactions.json');rows=json.loads(report.read_text()) if report.exists() else []
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=90)
 rows.append(dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr));report.write_text(json.dumps(rows,indent=2))
 assert p.returncode==0,rows[-1]
 return p.stdout
for unit in ['gdm','user@1002.service','user@1003.service']:
 assert subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip()=='inactive'
assert 'signatures OK' in run(['rpm','-K',original])
if sys.argv[1]=='prepare':
 assert run(['rpm','-q','--qf','%{VERSION}-%{RELEASE}',name])=='48.0-160100.2.1'
 assert subprocess.run(['rpm','-q',lang],capture_output=True).returncode==1
 assert run(['rpm','-V',name])==''
 baseline=dict(binary_sha256=hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest(),keys=run(['rpm','-qa','gpg-pubkey']).splitlines())
 P('/root/portal-staging-baseline.json').write_text(json.dumps(baseline))
 # The public key was checked against the repository-pinned fingerprint on host.
 run(['rpm','--import','/root/portal-staging.key'])
 for file in [candidate,translations]:assert 'signatures OK' in run(['rpm','-K',file])
 for option in ['-qlp','--scripts']:
  def query(file):return run(['rpm',option,file] if option=='-qlp' else ['rpm','-qp',option,file])
  assert query(original)==query(candidate),option
 release=run(['rpm','-qp','--qf','%{RELEASE}',candidate])
 for left,right in [(release,'160100.2.1'),('160100.2.2',release)]:
  assert run(['rpm','--eval','%{lua:print(rpm.vercmp("'+left+'","'+right+'"))}']).strip()=='1'
 run(['rpm','-Uvh','--test',candidate,translations]);run(['rpm','-Uvh',candidate,translations])
 assert run(['rpm','-V',name,lang])==''
 run(['rpm','-e',lang]);run(['rpm','-Uvh','--oldpackage',original]);assert run(['rpm','-V',name])==''
 assert hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest()==baseline['binary_sha256']
 run(['rpm','-e','--test',name]);run(['rpm','-e',name])
 try:run(['rpm','-ivh',candidate,translations])
 except BaseException:
  run(['rpm','-Uvh','--oldpackage',original]);raise
 assert run(['rpm','-V',name,lang])==''
 expected=dict(nevra=run(['rpm','-q',name]).strip(),rpm_sha256=hashlib.sha256(P(candidate).read_bytes()).hexdigest(),binary_sha256=hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest(),signed=True)
 P('/root/portal-rpm-expected.json').write_text(json.dumps(expected,indent=2));print(json.dumps(expected))
elif sys.argv[1]=='restore':
 run(['rpm','-e',lang]);run(['rpm','-Uvh','--oldpackage',original]);assert run(['rpm','-V',name])==''
 assert run(['rpm','-q','--qf','%{VERSION}-%{RELEASE}',name])=='48.0-160100.2.1'
 baseline=json.loads(P('/root/portal-staging-baseline.json').read_text())
 assert hashlib.sha256(P('/usr/libexec/'+name).read_bytes()).hexdigest()==baseline['binary_sha256']
 added=set(run(['rpm','-qa','gpg-pubkey']).splitlines())-set(baseline['keys'])
 assert all(p.startswith('gpg-pubkey-7edca82e-') for p in added),added
 if added:run(['rpm','-e',*sorted(added)])
 assert set(run(['rpm','-qa','gpg-pubkey']).splitlines())==set(baseline['keys'])
 print('Original signed SUSE RPM and trusted-key set restored')
else:raise SystemExit('expected prepare or restore')
