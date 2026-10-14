"""The options-file migration keeps every active value, drops only the retired
lines, writes nothing on a dry run, and refuses rather than guessing.
Run with py -3.7 tools/test_migrate_cfg_v14o.py.
"""
import os
import tempfile
import unittest

import test_scanner_v5 as env    # the shared stubs, so settings imports cleanly
import migrate_cfg_v14o as migrate

settings = env.settings

LEGACY = """# old layout
[features]
sim actions = on
object names = off
keyboard = on
numpad navigation = on
scanner = on
scanner swallow = off
captions = on
startup speech = off
travel list = off
build controls = on
scanner mode = on

[speech]
mode = manual
braille = full
logging = on
tooltip delay = 2.5

[voice]
rate = -3
volume = 55
name = david

[behavior]
auto focus = on
"""


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.saved = dict(settings._stored)
        self.addCleanup(lambda: (settings._stored.clear(), settings._stored.update(self.saved)))
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.cfg = os.path.join(self.folder.name, 'tyjokr_ScreenReader.cfg')
        with open(self.cfg, 'w', encoding='utf-8') as handle:
            handle.write(LEGACY)
        self.lines = []

    def run_migration(self, **kwargs):
        kwargs.setdefault('closed', lambda: True)
        kwargs.setdefault('backup', os.path.join(self.folder.name, 'backup'))
        return migrate.migrate(self.cfg, out=self.lines.append, **kwargs)

    def text(self):
        with open(self.cfg, encoding='utf-8') as handle:
            return handle.read()

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self.run_migration(), 0)
        self.assertEqual(self.text(), LEGACY)
        self.assertFalse(os.path.exists(os.path.join(self.folder.name, 'backup')))

    def test_write_keeps_every_value_and_drops_only_retired_lines(self):
        before, _ = migrate.parse(self.cfg)
        self.assertEqual(self.run_migration(write=True), 0)
        after, warnings = migrate.parse(self.cfg)
        self.assertEqual(after, before)
        self.assertEqual(warnings, [])
        text = self.text()
        for gone in ('scanner swallow', 'auto focus', '[behavior]'):
            self.assertNotIn(gone, text)
        self.assertIn('scanner mode = on', text)
        self.assertIn('volume = 55', text)
        with open(os.path.join(self.folder.name, 'backup', 'tyjokr_ScreenReader.cfg'), encoding='utf-8') as handle:
            self.assertEqual(handle.read(), LEGACY)
        self.assertNotIn(chr(0x2014), text)

    def test_refuses_while_the_game_runs(self):
        self.assertEqual(self.run_migration(write=True, closed=lambda: False), 5)
        self.assertEqual(self.text(), LEGACY)

    def test_refuses_a_file_with_warnings(self):
        with open(self.cfg, 'a', encoding='utf-8') as handle:
            handle.write('\n[speech]\nmode = shouting\n')
        self.assertEqual(self.run_migration(write=True), 3)
        self.assertTrue(any('refused' in line for line in self.lines))

    def test_already_simplified_file_is_left_alone(self):
        self.run_migration(write=True)
        first = self.text()
        self.assertEqual(self.run_migration(write=True, backup=os.path.join(self.folder.name, 'b2')), 0)
        self.assertEqual(self.text(), first)


if __name__ == '__main__':
    unittest.main()
