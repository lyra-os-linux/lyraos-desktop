import pathlib,subprocess
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
def run(a):subprocess.run(a,check=True)
source=pathlib.Path('/tmp/lyra-parental-probe.cil').read_text()
source+='''\n; Experimental PAM entry role. Not a complete login/session policy.
(role lyra_parental_r)
(roletype lyra_parental_r lyra_parental_probe_t)
(roleallow system_r lyra_parental_r)
(allow init_t lyra_parental_probe_t (process (transition)))
(allow local_login_t lyra_parental_probe_t (process (transition)))
(allow xdm_t lyra_parental_probe_t (process (transition)))
'''
pathlib.Path('/tmp/lyra-parental-probe.cil').write_text(source)
# Replace original module, avoiding duplicate type declarations.
run(['semodule','-i','/tmp/lyra-parental-probe.cil'])
run(['semanage','user','-a','-R','lyra_parental_r','-L','s0','-r','s0','lyra_parental_u'])
run(['semanage','login','-a','-s','lyra_parental_u','-r','s0','parentaltest'])
p=pathlib.Path('/etc/selinux/targeted/contexts/users/lyra_parental_u')
p.write_text(''.join(f'system_r:{t}:s0 lyra_parental_r:lyra_parental_probe_t:s0\n' for t in ['unconfined_service_t','init_t','local_login_t','xdm_t','sshd_t','crond_t']))
# No auth bypass on any real login service: a root-only test harness uses this
# dedicated session-only stack, never PAM authentication.
pathlib.Path('/etc/pam.d/lyra-parental-probe').write_text('session required pam_selinux.so close\nsession required pam_selinux.so open nottys\n')
run(['restorecon','-RF',str(p),'/etc/pam.d/lyra-parental-probe'])
