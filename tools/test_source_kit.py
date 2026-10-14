"""Source kit assembly: private-path redaction, the leak stop, and the
baseline checks that keep an old reviewed candidate from vouching for new
sources. Hermetic: temporary folders only, no game or FFDec needed."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

import make_source_kit as kit

BS = chr(92)
HOME = 'C:' + BS + 'Users' + BS + 'someone'
PROJECT = Path('C:' + BS + 'Users' + BS + 'someone' + BS + 'Work' + BS + 'Mod Project')
WORKSPACE = PROJECT.parent
ORIGINALS = [(PROJECT, '<original-project>'), (WORKSPACE, '<original-workspace>')]


class RedactionTests(unittest.TestCase):
    def test_every_spelling_of_a_profile_path_is_replaced(self):
        samples = [
            'from `' + HOME + BS + 'Downloads' + BS + 'review' + BS + '` today',
            '"path": "C:' + BS * 2 + 'Users' + BS * 2 + 'someone' + BS * 2 + 'AppData"',
            'All under `' + '/'.join(['C:', 'Users', 'someone', 'AppData', 'Local', 'Temp']) + '/`:',
            'ran /' + '/'.join(['c', 'Users', 'someone', 'Documents', 'x.py']) + ' here',
        ]
        for text in samples:
            cleaned = kit.redact(text, ORIGINALS)
            self.assertNotIn('someone', cleaned, text)
            self.assertIn('<user-home>', cleaned, text)
            self.assertEqual(kit.private_hits(cleaned), [], cleaned)

    def test_known_folders_get_their_own_placeholders(self):
        text = ('see ' + str(PROJECT) + BS + 'flash' + BS + 'chain.ps1 and '
                + str(WORKSPACE).replace(BS, '/') + '/voice and /'
                + '/'.join(['c', 'Users', 'someone', 'Work', 'Mod Project', 'tools']))
        cleaned = kit.redact(text, ORIGINALS)
        self.assertIn('<original-project>' + BS + 'flash', cleaned)
        self.assertIn('<original-workspace>/voice', cleaned)
        self.assertIn('<original-project>/tools', cleaned)
        self.assertNotIn('someone', cleaned)

    def test_module_names_and_credits_survive(self):
        text = 'tyjokr_a11y_keys.py by tyjokr and LeonianUniverse; Users can press Tab.'
        self.assertEqual(kit.redact(text, ORIGINALS), text)

    def test_generic_onedrive_advice_survives(self):
        for text in ('Options.ini in Documents, or the OneDrive or\ncustom user folder your game uses.',
                     'including OneDrive Documents if applicable.',
                     'including OneDrive/localized Documents if relevant.',
                     'Windows resolves redirected Documents (including OneDrive). The install',
                     'installed to the OneDrive\nworking folder',
                     'Copy the pair to OneDrive after backing up what is there; hash-check.',
                     "New-Folder 'redirected OneDrive" + BS + 'Documents' + BS + 'Electronic Arts' + BS + "Die Sims 4'"):
            self.assertEqual(kit.redact(text, ORIGINALS), text, text)
            self.assertEqual(kit.private_hits(text), [], text)

    def test_a_personal_onedrive_layout_is_replaced(self):
        text = '| OneDrive `Games/Stuff/Mods/Working-Copy/` | pair |'
        cleaned = kit.redact(text, ORIGINALS)
        self.assertEqual(cleaned, '| OneDrive `<private-folder>` | pair |')
        self.assertEqual(kit.private_hits(text), ['OneDrive folder path'])
        attached = 'saved in OneDrive' + BS + 'Games' + BS + 'Stuff' + BS + 'x.package ok'
        self.assertNotIn('Games', kit.redact(attached, ORIGINALS))


class KitTreeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def write(self, rel, text):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode('utf-8'))
        return path

    def test_docs_are_cleaned_in_place_but_code_stops_assembly(self):
        doc = self.write('docs/history/NOTE.md', 'Reviewed from `' + HOME + BS + 'Downloads' + BS + 'x' + BS + '`\n')
        self.write('docs/data.json', '{"readme": "' + str(PROJECT).replace(BS, BS * 2) + BS * 2 + 'README.txt"}\n')
        self.write('Scripts/clean.py', 'x = 1\n')
        self.write('tools/test_fixture.ps1', "New-Folder 'redirected OneDrive" + BS + 'Documents' + BS + "Electronic Arts'\n")
        self.assertEqual(kit.redact_kit(self.root, ORIGINALS), {})
        self.assertNotIn('someone', doc.read_text(encoding='utf-8'))
        self.assertIn('<original-project>', (self.root / 'docs/data.json').read_text(encoding='utf-8'))
        self.write('Scripts/leaky.py', "LOG = r'" + HOME + BS + "log.txt'\n")
        leaks = kit.redact_kit(self.root, ORIGINALS)
        self.assertEqual(list(leaks), ['Scripts/leaky.py'])
        self.assertIn('someone', (self.root / 'Scripts/leaky.py').read_text(encoding='utf-8'))

    def test_a_bom_is_kept_when_a_doc_is_rewritten(self):
        path = self.root / 'README.txt'
        path.write_bytes(b'\xef\xbb\xbf' + ('see ' + HOME + BS + 'x\n').encode('utf-8'))
        kit.redact_kit(self.root, ORIGINALS)
        self.assertTrue(path.read_bytes().startswith(b'\xef\xbb\xbfsee <user-home>'))
        self.assertNotIn(b'someone', path.read_bytes())

    def test_runtime_set_must_equal_the_reviewed_set(self):
        a = self.write('Scripts/tyjokr_a.py', 'a = 1\n')
        self.write('Scripts/ctypes/__init__.py', '\n')
        frozen = {'tyjokr_a.py': hashlib.sha256(a.read_bytes()).hexdigest(),
                  'ctypes/__init__.py': hashlib.sha256(b'\n').hexdigest()}
        kit.check_scripts(self.root, frozen)
        self.write('Scripts/tyjokr_new.py', 'b = 2\n')
        with self.assertRaises(SystemExit) as added:
            kit.check_scripts(self.root, frozen)
        self.assertIn("added=['tyjokr_new.py']", str(added.exception))
        (self.root / 'Scripts/tyjokr_new.py').unlink()
        (self.root / 'Scripts/ctypes/__init__.py').unlink()
        with self.assertRaises(SystemExit) as removed:
            kit.check_scripts(self.root, frozen)
        self.assertIn("removed=['ctypes/__init__.py']", str(removed.exception))

    def test_kit_copies_are_preferred_over_the_original_workspace(self):
        original = self.write('workspace/names.tsv', 'a\n')
        self.assertEqual(kit.pick(self.root / 'reference/names.tsv', original), original)
        own = self.write('reference/names.tsv', 'b\n')
        self.assertEqual(kit.pick(own, original), own)
        with self.assertRaises(FileNotFoundError):
            kit.pick(self.root / 'nope', self.root / 'also-nope')

    def test_recorded_paths_resolve_relative_absolute_or_beside_the_candidate(self):
        release = self.root / 'candidate'
        moved = self.write('candidate/script-manifest.json', '{}')
        self.assertEqual(kit.recorded(str(moved), release), moved)
        self.assertEqual(kit.recorded('X:/elsewhere/build/script-manifest.json', release), moved)
        with self.assertRaises(FileNotFoundError):
            kit.recorded('X:/elsewhere/missing.json', release)

    def test_reuse_proof_must_match_the_reviewed_packages(self):
        reviewed = {'ui.package': 'aa', 'compat.package': 'bb'}
        self.assertIsNone(kit.reuse_proof(None, reviewed))
        devkit = self.write('final/ui-verification.json', json.dumps(
            {'ui.package': {'movies': 25, 'sha256': 'aa'}, 'compat.package': {'movies': 6, 'sha256': 'bb'}}))
        proof = kit.reuse_proof(devkit.parent, reviewed)
        self.assertTrue(proof['rebuilt_equal_to_reference'])
        self.assertEqual(proof['packages'], reviewed)
        release = self.write('release/ui-verification.json', json.dumps(
            {'live_verified': False, 'packages': {'ui.package': {'sha256': 'aa'}, 'compat.package': {'sha256': 'bb'}}}))
        self.assertEqual(kit.reuse_proof(release, reviewed)['packages'], reviewed)
        wrong = self.write('wrong/ui-verification.json', json.dumps({'ui.package': {'sha256': 'zz'}}))
        with self.assertRaises(SystemExit):
            kit.reuse_proof(wrong, reviewed)


if __name__ == '__main__':
    unittest.main(verbosity=2)
