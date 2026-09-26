import json, tempfile, unittest
from pathlib import Path
from unittest import mock

import cull_core
from cull_core import (find_exact_duplicates, find_near_name_groups, normalized_name,
                       quarantine, reclaimable_bytes, restore_quarantine)


class DuplicateDetectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.root = Path(self._tmp.name)
    def tearDown(self):
        self._tmp.cleanup()

    def write(self, rel, data):
        p = self.root / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(data); return p

    def test_same_size_different_content_is_not_a_duplicate(self):
        self.write('a.bin', b'abcd'); self.write('b.bin', b'wxyz')
        self.assertEqual(find_exact_duplicates(self.root), [])

    def test_duplicates_across_nested_folders_are_grouped(self):
        self.write('photos/2026/img.jpg', b'pixels'); self.write('downloads/img (1).jpg', b'pixels'); self.write('desktop/old/img.jpg', b'pixels')
        groups = find_exact_duplicates(self.root)
        self.assertEqual(len(groups), 1); self.assertEqual(len(groups[0].files), 3)
        self.assertEqual(reclaimable_bytes(groups), 2 * len(b'pixels'))

    def test_min_size_skips_small_and_empty_files(self):
        self.write('e1', b''); self.write('e2', b''); self.write('s1', b'x'); self.write('s2', b'x')
        self.assertEqual(find_exact_duplicates(self.root, min_size=2), [])
        self.assertEqual(len(find_exact_duplicates(self.root)), 1)  # default skips only empty files

    def test_groups_are_ordered_by_reclaimable_space(self):
        self.write('small1', b'a' * 10); self.write('small2', b'a' * 10)
        self.write('big1', b'b' * 100); self.write('big2', b'b' * 100)
        sizes = [g.size for g in find_exact_duplicates(self.root)]
        self.assertEqual(sizes, [100, 10])

    def test_ignored_folders_and_existing_quarantine_are_not_rescanned(self):
        self.write('keep.txt', b'same'); self.write('node_modules/pkg/keep.txt', b'same'); self.write('.cull-quarantine/old/keep.txt', b'same')
        self.assertEqual(find_exact_duplicates(self.root), [])

    def test_near_name_groups_ignore_copy_markers(self):
        self.write('Report.pdf', b'1'); self.write('Report copy (2).pdf', b'22'); self.write('report_final.pdf', b'333'); self.write('other.pdf', b'4')
        groups = find_near_name_groups(self.root)
        self.assertEqual(len(groups), 1); self.assertEqual(groups[0].key, 'report'); self.assertEqual(len(groups[0].files), 3)

    def test_names_that_normalize_to_nothing_are_not_grouped(self):
        self.assertEqual(normalized_name('copy.txt'), '')
        self.write('copy.txt', b'1'); self.write('backup.txt', b'2')
        self.assertEqual(find_near_name_groups(self.root), [])


class QuarantineTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(); self.root = Path(self._tmp.name)
    def tearDown(self):
        self._tmp.cleanup()

    def test_quarantine_preserves_relative_layout_and_writes_manifest(self):
        f = self.root / 'a' / 'b' / 'dup.txt'; f.parent.mkdir(parents=True); f.write_text('dup')
        batch = quarantine(self.root, [f])
        self.assertTrue((batch / 'a' / 'b' / 'dup.txt').exists())
        manifest = json.loads((batch / 'manifest.json').read_text())
        self.assertEqual(manifest['moved'][0]['from'], str(f.resolve()))

    def test_path_outside_root_moves_nothing(self):
        inside = self.root / 'in.txt'; inside.write_text('in')
        with tempfile.TemporaryDirectory() as other:
            outside = Path(other) / 'out.txt'; outside.write_text('out')
            with self.assertRaises(ValueError):
                quarantine(self.root, [inside, outside])
            self.assertTrue(inside.exists(), 'a valid file was moved before the invalid one was rejected')
            self.assertTrue(outside.exists())

    def test_two_quarantines_in_the_same_second_both_succeed(self):
        a = self.root / 'a.txt'; a.write_text('a'); b = self.root / 'b.txt'; b.write_text('b')
        with mock.patch.object(cull_core.time, 'strftime', return_value='20260926-120000'):
            first = quarantine(self.root, [a]); second = quarantine(self.root, [b])
        self.assertNotEqual(first, second)
        self.assertEqual(restore_quarantine(first), 1); self.assertEqual(restore_quarantine(second), 1)
        self.assertTrue(a.exists() and b.exists())

    def test_restore_never_overwrites_a_file_that_came_back(self):
        f = self.root / 'x.txt'; f.write_text('original')
        batch = quarantine(self.root, [f])
        f.write_text('new file at the same path')
        self.assertEqual(restore_quarantine(batch), 0)
        self.assertEqual(f.read_text(), 'new file at the same path')


if __name__ == '__main__':
    unittest.main()
