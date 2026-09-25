import pathlib,subprocess,os
assert os.geteuid()==0
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
for p in ['/usr/lib/systemd/user-environment-generators/30-systemd-environment-d-generator','/usr/lib/systemd/user-generators/systemd-xdg-autostart-generator']:
 assert pathlib.Path(p).read_bytes().startswith(b'\x7fELF')
 subprocess.run(['semanage','fcontext','-a','-t','lyra_parental_generator_exec_t',p],check=True)
 subprocess.run(['restorecon','-v',p],check=True)
