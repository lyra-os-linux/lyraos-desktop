import pathlib,subprocess
assert 'lyra.parental-selinux-test=1' in pathlib.Path('/proc/cmdline').read_text().split()
p=pathlib.Path('/tmp/lyra-parental-probe.cil');s=p.read_text();s+='\n; Test harness only: normal-account control from the evidence service.\n(allow unconfined_service_t unconfined_t (process (transition)))\n';p.write_text(s)
subprocess.run(['semodule','-i',str(p)],check=True)
