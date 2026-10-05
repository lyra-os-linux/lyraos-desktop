import importlib.machinery,importlib.util,os,tempfile,unittest
from pathlib import Path
FILE=Path(__file__).resolve().parents[1]/'packaging/lyra-release/lyra-release-identity'
s=importlib.util.spec_from_loader('release_identity',importlib.machinery.SourceFileLoader('release_identity',str(FILE)));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
VENDOR=b'NAME="openSUSE Leap"\nPRETTY_NAME="openSUSE Leap 16.1"\nID=opensuse-leap\nVERSION_ID="16.1"\nCPE_NAME="cpe:/o:opensuse:leap:16.1"\n'
class Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  for p in ('etc','usr/lib/lyra-os'): (self.root/p).mkdir(parents=True,exist_ok=True)
  (self.root/'usr/lib/os-release').write_bytes(VENDOR)
  (self.root/'usr/lib/lyra-os/product-release').write_bytes(b"LYRA_VERSION_ID='1.1'\nLYRA_EDITION='desktop'\n")
  self.target=self.root/'etc/os-release';self.target.symlink_to('../usr/lib/os-release')
 def apply(self):return m.apply(self.root,os.geteuid())
 def test_replaces_link_without_touching_vendor(self):self.assertEqual(self.apply()['PRETTY_NAME'],'Lyra OS 1.1');self.assertFalse(self.target.is_symlink());self.assertEqual((self.root/'usr/lib/os-release').read_bytes(),VENDOR)
 def test_reapplies_after_vendor_overwrites_link(self):
  self.apply();self.target.unlink();self.target.symlink_to('../usr/lib/os-release');self.assertEqual(self.apply()['NAME'],'Lyra OS')
 def test_repeated_apply_is_content_idempotent(self):self.apply();data=self.target.read_bytes();self.apply();self.assertEqual(self.target.read_bytes(),data)
 def test_image_metadata_survives(self):self.target.unlink();self.target.write_text('ID="lyra-os"\nIMAGE_ID="lyra-desktop"\nIMAGE_VERSION="alpha8"\nBUILD_ID="exact-image"\n');d=self.apply();self.assertEqual(d['BUILD_ID'],'exact-image');self.assertEqual(d['IMAGE_VERSION'],'alpha8')
 def test_image_metadata_survives_vendor_replacement(self):
  self.target.unlink();self.target.write_text('ID=lyra-os\nBUILD_ID=exact-image\nIMAGE_VERSION=alpha8\n');self.apply();self.target.unlink();self.target.symlink_to('../usr/lib/os-release');d=self.apply();self.assertEqual(d['BUILD_ID'],'exact-image');self.assertEqual(d['IMAGE_VERSION'],'alpha8')
 def test_removal_restores_original_link(self):self.apply();m.restore(self.root,os.geteuid());self.assertTrue(self.target.is_symlink());self.assertEqual(os.readlink(self.target),'../usr/lib/os-release')
 def test_removal_preserves_later_edits(self):self.apply();self.target.write_text('ID="local"\n');self.assertRaises(ValueError,m.restore,self.root,os.geteuid());self.assertEqual(self.target.read_text(),'ID="local"\n')
 def test_foreign_base_refused(self):(self.root/'usr/lib/os-release').write_text('ID="other"\nVERSION_ID="16.1"\n');self.assertRaises(ValueError,self.apply);self.assertTrue(self.target.is_symlink())
 def test_unknown_local_identity_preserved(self):self.target.unlink();self.target.write_text('ID="custom"\n');self.assertRaises(ValueError,self.apply);self.assertEqual(self.target.read_text(),'ID="custom"\n')
 def test_original_regular_file_restored(self):self.target.unlink();data=b'ID="lyra-os"\nBUILD_ID="old-image"\n';self.target.write_bytes(data);self.apply();m.restore(self.root,os.geteuid());self.assertEqual(self.target.read_bytes(),data)
if __name__=='__main__':unittest.main()
