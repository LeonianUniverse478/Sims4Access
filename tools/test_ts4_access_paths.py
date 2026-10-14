"""Exercise the real path functions against the renamed install layouts."""
import ast
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AccessPaths(unittest.TestCase):
    def test_prism_discovery_and_archive_location(self):
        source = ast.parse((ROOT / 'Scripts/tyjokr_a11y_speech.py').read_text(encoding='utf-8'))
        funcs = ast.Module(body=[n for n in source.body if isinstance(n, ast.FunctionDef)
                               and n.name in ('_mods_folder', '_mods_root', '_prism_path')])
        with tempfile.TemporaryDirectory() as tmp:
            mods = Path(tmp) / 'Mods'
            install = mods / 'TS4_Access'
            install.mkdir(parents=True)
            env = {'os': os, '__file__': str(install / 'TS4_Access.ts4script' / 'tyjokr_a11y_speech.pyc')}
            exec(compile(funcs, '<real path functions>', 'exec'), env)
            env['MODS_FOLDER'] = env['_mods_folder']()
            self.assertEqual(Path(env['MODS_FOLDER']), install)
            self.assertEqual(Path(env['_mods_root']()), mods)
            for dll in (install / 'TS4_Access_SpeechPack' / 'prism.dll',
                        mods / 'TS4_Access_SpeechPack' / 'prism.dll',
                        install / 'prism.dll'):
                dll.parent.mkdir(parents=True, exist_ok=True)
                dll.write_bytes(b'path-test-only')
                self.assertEqual(Path(env['_prism_path']()), dll)
                dll.unlink()

    def test_settings_filename(self):
        text = (ROOT / 'Scripts/tyjokr_a11y_settings.py').read_text(encoding='utf-8')
        self.assertIn("PATH = os.path.join(MODS_FOLDER, 'TS4_Access.cfg')", text)
        self.assertNotIn('tyjokr_ScreenReader.cfg', text)


if __name__ == '__main__':
    unittest.main()
