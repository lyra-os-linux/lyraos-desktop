"""Apply all SUSE patches, then the experimental direct-exec patch."""
import argparse,pathlib,re,subprocess,tarfile
p=argparse.ArgumentParser();p.add_argument('--sources',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--patch',type=pathlib.Path,default=pathlib.Path(__file__).with_name('xkb-direct-exec.patch'));a=p.parse_args()
assert not a.output.exists(), 'use a fresh output directory'
a.output.mkdir(parents=True)
with tarfile.open(a.sources/'xwayland-24.1.9.tar.xz') as t:t.extractall(a.output,filter='data')
root=a.output/'xwayland-24.1.9'
for name in re.findall(r'^Patch\d+:\s+(\S+)',(a.sources/'xwayland.spec').read_text(),re.M):
 subprocess.run(['patch','--batch','-p1','-i',str((a.sources/name).resolve())],cwd=root,check=True)
subprocess.run(['patch','--batch','-p1','-i',str(a.patch.resolve())],cwd=root,check=True)
print(root)
