import json
from pathlib import Path
import tempfile
import unittest
import zipfile

import source_exchange as exchange


class ExchangeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Scripts').mkdir()
        (self.root / 'Scripts/one.py').write_text('value = 1\n')
        (self.root / 'Scripts/remove.py').write_text('old = True\n')
        exchange.checkpoint(self.root)

    def changes(self):
        (self.root / 'Scripts/one.py').write_text('value = 2\n')
        (self.root / 'Scripts/remove.py').unlink()
        (self.root / 'Scripts/new.py').write_text('new = True\n')
        return exchange.make_return(self.root, 'Update example', 'Offline only')

    def rewrite(self, archive, change):
        with zipfile.ZipFile(str(archive)) as z:
            contents = {n: z.read(n) for n in z.namelist()}
        change(contents)
        out = self.root / 'malformed.zip'
        with zipfile.ZipFile(str(out), 'w') as z:
            for n, b in contents.items(): z.writestr(n, b)
        return out

    def test_roundtrip_add_edit_delete_never_changes_receiver_source(self):
        archive = self.changes()
        (self.root / 'Scripts/one.py').write_text('value = 1\n')
        before = (self.root / 'Scripts/one.py').read_bytes()
        out, conflicts = exchange.review(self.root, archive)
        self.assertEqual(conflicts, 0)
        self.assertEqual((self.root / 'Scripts/one.py').read_bytes(), before)
        self.assertEqual((out / 'files/Scripts/new.py').read_text(), 'new = True\n')
        self.assertIn('delete', (out / 'REPORT.md').read_text())

    def test_receiver_edit_is_a_conflict_not_overwritten(self):
        archive = self.changes()
        (self.root / 'Scripts/one.py').write_text('value = 99\n')
        out, conflicts = exchange.review(self.root, archive)
        self.assertEqual(conflicts, 1)
        self.assertEqual((self.root / 'Scripts/one.py').read_text(), 'value = 99\n')

    def test_traversal_and_windows_aliases_are_rejected(self):
        for n in ['../Scripts/one.py', '/Scripts/one.py', 'Scripts/../one.py',
                  'Scripts/a.py:stream', 'Scripts/CON.py', 'Scripts/a.py.',
                  'Scripts\\a.py', 'Scripts/a\nb.py', 'Scripts//a.py']:
            self.assertFalse(exchange.allowed(n), n)

    def test_invalid_return_path_rejected_before_extraction(self):
        archive = self.changes()
        def alter(contents):
            m = json.loads(contents['RETURN.json']);m['changes'][0]['path'] = '../bad.py'
            contents['RETURN.json'] = json.dumps(m).encode()
        bad = self.rewrite(archive, alter)
        with self.assertRaises(ValueError): exchange.review(self.root, bad)
        self.assertFalse((self.root / 'reviews').exists())

    def test_wrong_baseline_rejected(self):
        archive = self.changes()
        def alter(contents):
            m = json.loads(contents['RETURN.json']);m['baseline_id'] = 'wrong'
            contents['RETURN.json'] = json.dumps(m).encode()
        with self.assertRaisesRegex(ValueError, 'Different handoff'):
            exchange.review(self.root, self.rewrite(archive, alter))

    def test_tampered_payload_and_unexpected_files_rejected(self):
        archive = self.changes()
        bad = self.rewrite(archive, lambda c: c.update({'files/Scripts/one.py': b'evil = True\n'}))
        with self.assertRaisesRegex(ValueError, 'Payload hash'): exchange.review(self.root, bad)
        bad = self.rewrite(archive, lambda c: c.update({'config.cfg': b'not source'}))
        with self.assertRaisesRegex(ValueError, 'Unexpected ZIP'): exchange.review(self.root, bad)

    def test_no_configs_or_build_outputs_in_return(self):
        (self.root / 'dev.local.json').write_text('{"private":"local"}')
        (self.root / 'Scripts/player.cfg').write_text('private')
        with self.assertRaisesRegex(ValueError, 'No source changes'):
            exchange.make_return(self.root, 'none', 'none')

    def test_diff_preserves_missing_final_newline(self):
        (self.root / 'Scripts/one.py').write_bytes(b'value = 2')
        (self.root / 'Scripts/z.py').write_bytes(b'z = 1')
        archive = exchange.make_return(self.root, 'No trailing newline', 'test')
        with zipfile.ZipFile(str(archive)) as z:
            patch = z.read('CHANGES.patch').decode()
        self.assertIn('+value = 2\n\\ No newline at end of file\n', patch)
        self.assertIn('\n--- /dev/null\n', patch)
        out, _ = exchange.review(self.root, archive)
        self.assertEqual((out / 'CHANGES.patch').read_bytes().decode(), patch)

    def test_malformed_return_reports_value_error_before_extraction(self):
        archive = self.changes()
        for alter in (lambda c: c.pop('RETURN.json'),
                      lambda c: c.update({'RETURN.json': b'{"format": 1}'}),
                      lambda c: c.update({'RETURN.json': b'[]'})):
            with self.assertRaises(ValueError):
                exchange.review(self.root, self.rewrite(archive, alter))
        self.assertFalse((self.root / 'reviews').exists())

    def test_case_variant_baseline_add_is_rejected(self):
        archive = self.changes()
        def alter(contents):
            m = json.loads(contents['RETURN.json'])
            row = next(c for c in m['changes'] if c['path'] == 'Scripts/one.py')
            row['path'] = 'Scripts/ONE.py'; row['before'] = None
            contents['files/Scripts/ONE.py'] = contents.pop('files/Scripts/one.py')
            contents['RETURN.json'] = json.dumps(m).encode()
        with self.assertRaisesRegex(ValueError, 'Case-variant'):
            exchange.review(self.root, self.rewrite(archive, alter))
        self.assertFalse((self.root / 'reviews').exists())


if __name__ == '__main__': unittest.main()
