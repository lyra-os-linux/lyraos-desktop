import pathlib,subprocess,shutil,os
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
b=pathlib.Path('/opt/lyra-parental-probe')
for name in ('bus-service','unapproved-bus-service'):assert not (b/name).exists()
subprocess.run(['gcc','-Wall','-Wextra','-Werror','/tmp/lyra-parental-service.c','-lsystemd','-o',str(b/'bus-service')],check=True)
shutil.copy2(b/'bus-service',b/'unapproved-bus-service')
subprocess.run(['chcon','-t','lyra_parental_probe_exec_t',str(b/'bus-service')],check=True)
subprocess.run(['chcon','-t','bin_t',str(b/'unapproved-bus-service')],check=True)
print(subprocess.check_output(['ls','-lZ',str(b/'bus-service'),str(b/'unapproved-bus-service')],text=True))
