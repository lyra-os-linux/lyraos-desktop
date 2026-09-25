import pathlib,subprocess,shutil,os
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
p=pathlib.Path('/opt/lyra-parental-probe/busctl')
assert not p.exists()
shutil.copy2('/usr/bin/busctl',p)
subprocess.run(['chcon','-t','lyra_parental_probe_exec_t',str(p)],check=True)
print(subprocess.check_output(['ls','-lZ',str(p)],text=True))
