import json,pathlib,subprocess
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
old='/root/portal-original.rpm';new='/root/portal-rpmbuild/RPMS/x86_64/xdg-desktop-portal-gnome-48.0-160100.2.1.lyra1.x86_64.rpm'
def query(file,*args):return subprocess.check_output(['rpm','-qp',*args,file],text=True)
report={}
for option in ['--requires','--provides','--scripts','--dump']:
 report[option]=dict(original=query(old,option).splitlines(),candidate=query(new,option).splitlines())
a={l.split()[0]:l.split() for l in report['--dump']['original']};b={l.split()[0]:l.split() for l in report['--dump']['candidate']}
assert a.keys()==b.keys()
changed=[name for name in a if a[name][3]!=b[name][3]]
assert changed==['/usr/libexec/xdg-desktop-portal-gnome'],changed
removed=set(report['--requires']['original'])-set(report['--requires']['candidate'])
added=set(report['--requires']['candidate'])-set(report['--requires']['original'])
assert not removed and added=={'libc.so.6(GLIBC_2.38)(64bit)'},(removed,added)
provider=subprocess.check_output(['rpm','-q','--whatprovides',*sorted(added)],text=True).strip()
report['dependency_delta']=dict(removed=sorted(removed),added=sorted(added),installed_provider=provider)
assert report['--scripts']['original']==report['--scripts']['candidate']
for left,right in [('160100.2.1.lyra1','160100.2.1'),('160100.2.2','160100.2.1.lyra1')]:
 result=subprocess.check_output(['rpm','--eval','%{lua:print(rpm.vercmp("'+left+'", "'+right+'"))}'],text=True).strip()
 assert result=='1',(left,right,result)
report.update(passed=True,changed_payload_digests=changed,release_order_validated=True)
P('/root/portal-rpm-inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(passed=True,changed_payload_digests=changed,dependencies_delta=report['dependency_delta'],release_order_validated=True)))
