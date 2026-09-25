"""Apply the diagnostic hook patch to an extracted official AT-SPI SRPM."""
import argparse,pathlib,subprocess,tarfile
parser=argparse.ArgumentParser()
parser.add_argument('--sources',type=pathlib.Path,required=True)
parser.add_argument('--output',type=pathlib.Path,required=True)
args=parser.parse_args()
assert not args.output.exists(), 'Output must be new'
args.output.mkdir(parents=True)
with tarfile.open(args.sources/'at-spi2-core-2.58.7.tar.xz') as archive:
    archive.extractall(args.output,filter='data')
tree=args.output/'at-spi2-core-2.58.7'
subprocess.run(['patch','--batch','--forward','-p1','-i',str(pathlib.Path(__file__).with_name('native-x11-hook.patch').resolve())],cwd=tree,check=True)
print(tree)
