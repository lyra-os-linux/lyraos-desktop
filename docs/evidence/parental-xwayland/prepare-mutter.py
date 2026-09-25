"""Apply SUSE patches/subproject and the experimental read-only FD patch."""
import argparse,pathlib,re,subprocess,tarfile
p=argparse.ArgumentParser();p.add_argument('--sources',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--patch',type=pathlib.Path,default=pathlib.Path(__file__).with_name('mutter-readonly-fd.patch'));a=p.parse_args()
assert not a.output.exists(), 'use a fresh output directory'
a.output.mkdir(parents=True)
with tarfile.open(a.sources/'mutter-48.8.tar.xz') as t:t.extractall(a.output,filter='data')
root=a.output/'mutter-48.8'
for name in re.findall(r'^Patch\d+:\s+(\S+)',(a.sources/'mutter.spec').read_text(),re.M):
 subprocess.run(['patch','--batch','-p1','-i',str((a.sources/name).resolve())],cwd=root,check=True)
with tarfile.open(a.sources/'gvdb-0.gitmodule.tar.xz') as t:t.extractall(root/'subprojects',filter='data')
(root/'subprojects/gvdb-0.gitmodule').rename(root/'subprojects/gvdb')
subprocess.run(['patch','--batch','-p1','-i',str(a.patch.resolve())],cwd=root,check=True)
subprocess.run(['patch','--batch','-p1','-i',str(pathlib.Path(__file__).with_name('mutter-frames-failure.patch').resolve())],cwd=root,check=True)
print(root)
