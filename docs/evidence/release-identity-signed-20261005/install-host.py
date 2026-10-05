#!/usr/bin/python3
"""Install only the reviewed accepted release RPM from the OBS API and record host checks."""
from pathlib import Path
import hashlib,json,os,shlex,subprocess,sys,rpm,xml.etree.ElementTree as ET
assert os.geteuid()==0
out=Path(__file__).resolve().parent
manifest=json.loads((out/'release-api-verification.json').read_text())
assert manifest['signing_fingerprint']=='399218A6E088C4053F4533BE58097F767EDCA82E'
assert manifest['submit_request']==1382519 and manifest['source_srcmd5']=='67be43654954516ff5d765a0244e47f4'
request=ET.parse(out/'request-1382519-accepted.xml').getroot()
assert request.get('id')=='1382519' and request.find('state').get('name')=='accepted'
source=request.find('action/source'); target=request.find('action/target')
assert source.get('rev')==manifest['source_srcmd5'] and source.get('project')=='home:rodrigosbrito:lyra:staging'
assert target.get('project')=='home:rodrigosbrito:lyra' and target.get('package')=='lyra-release'
assert json.loads((out/'release-payload-comparison.json').read_text())['passed'] is True
package=manifest['packages'][0]
assert package['name']=='lyra-release' and package['architecture']=='noarch' and package['signature']=='verified'
assert manifest['delivery']=='obs_api' and manifest['public_release_verified'] is False
artifact=out/'release-api-rpms'/package['filename']
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(artifact)==package['sha256']
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=180)
 row=dict(args=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr)
 if p.returncode:raise RuntimeError(row)
 return row
def identity():
 return dict((k,shlex.split(v)[0]) for k,v in (line.split('=',1) for line in Path('/etc/os-release').read_text().splitlines() if line and not line.startswith('#')))
assert identity()['LYRA_BASE_ID']=='opensuse-leap' and identity()['LYRA_BASE_VERSION_ID']=='16.1'
before=dict(vendor_sha256=sha('/usr/lib/os-release'),product_sha256=sha('/usr/lib/lyra-os/product-release'),nevra=run(['rpm','-q','lyra-release'])['stdout'].strip())
old=run(['rpm','-q','--qf','%{EPOCHNUM} %{VERSION} %{RELEASE}','lyra-release'])['stdout'].split()
new=run(['rpm','-qp','--qf','%{EPOCHNUM} %{VERSION} %{RELEASE}',str(artifact)])['stdout'].split()
assert rpm.labelCompare(tuple(new),tuple(old))>0
sig=run(['rpmkeys','--dbpath',str(out/'rpmdb'),'--checksig',str(artifact)])
install=run(['zypper','--non-interactive','--no-refresh','install','--no-recommends',str(artifact)])
after=dict(vendor_sha256=sha('/usr/lib/os-release'),product_sha256=sha('/usr/lib/lyra-os/product-release'),nevra=run(['rpm','-q','lyra-release'])['stdout'].strip(),identity=identity())
assert after['vendor_sha256']==before['vendor_sha256'] and after['product_sha256']==before['product_sha256']
assert after['identity']['PRETTY_NAME']=='Lyra OS 1.1' and after['identity']['LOGO']=='distributor-logo-lyra'
verify=run(['rpm','-V','lyra-release'])
assert sha('/usr/libexec/lyra-release-identity')==sha(out/'extract-staging/usr/libexec/lyra-release-identity')
state=json.loads(Path('/var/lib/lyra-release/identity-state.json').read_text())
assert state['managed_sha256']==sha('/etc/os-release') and state['vendor_sha256']==after['vendor_sha256']
row=dict(passed=True,before=before,after=after,signature=sig,install=install,rpm_verify=verify,release_rpm_sha256=package['sha256'],only_requested_package='lyra-release',delivery='obs_api',submit_request=1382519,public_release_verified=False)
(out/'host-install.json').write_text(json.dumps(row,indent=2)+'\n')
print(json.dumps(row,indent=2))
