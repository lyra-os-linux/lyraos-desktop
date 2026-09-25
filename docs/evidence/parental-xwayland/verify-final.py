import pathlib,subprocess,hashlib,json
P=pathlib.Path
assert 'lyra.parental-selinux-test=1' in P('/proc/cmdline').read_text().split()
rows=[]
def run(args):
 p=subprocess.run(args,capture_output=True,text=True,timeout=15)
 r=dict(argv=args,rc=p.returncode,stdout=p.stdout,stderr=p.stderr);rows.append(r);return r
r=run(['rpm','-V','gdm','mutter','xwayland','gnome-shell','gnome-session-core','gnome-session-wayland','at-spi2-core','xprop','xkbcomp']);assert r['rc']==0 and not r['stdout']
for s in ['gdm','user@1003.service','auditd']:assert run(['systemctl','is-active',s])['stdout'].strip()=='inactive'
absent=['/root/lyra-xwayland-recovery/active.json','/usr/libexec/lyra/trusted-shell-test','/etc/systemd/user/org.gnome.Shell@wayland.service.d/99-lyra-trusted-test.conf','/etc/dconf/profile/lyra-supervised-test','/etc/dconf/db/lyra-supervised-test','/etc/pam.d/gdm-autologin','/etc/gdm/custom.conf.lyra-baseline','/tmp/lyra-trusted-shell-test.log','/run/user/1003','/etc/selinux/targeted/active/modules/400/lyra-trusted-shell-test']
assert all(not P(p).exists() for p in absent)
assert P('/sys/fs/selinux/enforce').read_text().strip()=='0'
status=run(['auditctl','-s'])['stdout'];assert 'backlog_limit 64\n' in status
assert P('/etc/selinux/targeted/active/modules/400/lyra-parental-probe').exists()
print(json.dumps(dict(passed=True,commands=rows,absent=absent,selinux='permissive outside test',worker_sha256=hashlib.sha256(P('/usr/libexec/gdm/gdm-session-worker').read_bytes()).hexdigest()),indent=2))
