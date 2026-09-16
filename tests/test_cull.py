import tempfile, unittest
from pathlib import Path
from cull_core import find_exact_duplicates, reclaimable_bytes, normalized_name, quarantine, restore_quarantine
class CullTests(unittest.TestCase):
    def test_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'a.txt').write_text('x'); (p/'b.txt').write_text('x'); (p/'c.txt').write_text('y')
            g=find_exact_duplicates(p); self.assertEqual(len(g),1); self.assertEqual(len(g[0].files),2); self.assertEqual(reclaimable_bytes(g),1)
    def test_name_normalization(self): self.assertEqual(normalized_name('Report copy (2).pdf'),'report')
    def test_quarantine_restore(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); f=p/'x.txt'; f.write_text('abc'); b=quarantine(p,[f]); self.assertFalse(f.exists()); self.assertEqual(restore_quarantine(b),1); self.assertTrue(f.exists())
if __name__=='__main__': unittest.main()