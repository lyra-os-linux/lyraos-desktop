import pathlib,subprocess
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
def run(args):subprocess.run(args,check=True)
run(['gcc','-shared','-fPIC','-Wall','-Wextra','-Werror','-O2','/root/lyra-parental-pam-guard.c','-o','/usr/lib64/security/pam_lyra_fixture_guard.so','-lpam','-lselinux'])
run(['groupadd','lyra-parental-fixture'])
run(['usermod','-aG','lyra-parental-fixture','parentaltest'])
p=pathlib.Path('/etc/pam.d/lyra-parental-probe');p.write_text(p.read_text()+'session required pam_lyra_fixture_guard.so\n')
run(['restorecon','/usr/lib64/security/pam_lyra_fixture_guard.so',str(p)])
