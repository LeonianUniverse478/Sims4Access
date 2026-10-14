"""TS4 Access Plus merged into TS4 Access (2026-10-08): every module loads on
its own, the Alt-key table is the add-on's (Alt+Q opens TS4 Access's own
queue), nothing is written to disk outside the installed mod, and the
catalog bridge replies (a11yplus.flash) are parsed."""
import os
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_plus as plus
import tyjokr_a11y_plus_build as build
import tyjokr_a11y_plus_core as core
import tyjokr_a11y_plus_menu as menu


class PlusTests(unittest.TestCase):
    def test_every_module_loads(self):
        self.assertEqual(plus.failed, [])
        self.assertEqual(plus.loaded, list(plus.MODULES))

    def test_loaded_at_startup(self):
        with open(env.ROOT / 'Scripts' / 'tyjokr_a11y_keys.py', encoding='utf-8') as handle:
            self.assertIn('import tyjokr_a11y_plus ', handle.read())

    def test_alt_keys(self):
        keys = dict((vk, desc) for vk, (_fn, desc) in core.HOTKEYS.items())
        for letter, desc in (('A', 'Access Plus menu'), ('N', 'read needs'), ('T', 'time and day'),
                             ('Q', 'action queue'), ('R', 'rooms'), ('W', 'where am I'),
                             ('L', 'last notifications'), ('C', 'create and edit Sims'), ('B', 'build helper'),
                             ('S', 'drawing cursor: mark start'), ('D', 'drawing cursor: draw'),
                             ('X', 'drawing cursor: where am I'), ('Z', 'drawing cursor: undo')):
            self.assertEqual(keys.get(ord(letter)), desc, letter)
        for vk in (0x25, 0x26, 0x27, 0x28):
            self.assertIn(vk, keys)
        self.assertEqual(len(keys), 17)

    def test_alt_q_opens_the_ts4_access_queue(self):
        import tyjokr_a11y_hub as hub
        with patch.object(hub, 'action_queue', return_value=True) as queue:
            core.HOTKEYS[ord('Q')][0]()
        queue.assert_called_once_with()
        self.assertFalse(any(name.endswith('plus_queue') for name in sys.modules))

    def test_no_files_outside_the_installed_mod(self):
        self.assertFalse(core.IN_GAME)
        before = set(os.listdir(core.MODS_FOLDER))
        core.log('test line')
        core._save_settings()
        self.assertEqual(set(os.listdir(core.MODS_FOLDER)), before)
        self.assertFalse(os.path.exists(core.HOME_LOG_PATH) and 'test line' in open(core.HOME_LOG_PATH).read())

    def test_catalog_replies(self):
        build._cat.update(serial=7, items=[], total=0, name='Doors', next='wall', quiet=None)
        from urllib.parse import quote
        page = quote('cat|7|0|2|' + quote('Front Door') + '~350~4^' + quote('Back Door') + '~120~1')
        build._flash_reply(page)
        self.assertEqual(build._cat['items'], [('Front Door', 350, 4), ('Back Door', 120, 1)])
        self.assertEqual(build._cat['total'], 2)
        build._flash_reply(quote('cat|6|0|1|' + quote('Stale') + '~1~1'))
        self.assertEqual(len(build._cat['items']), 2, 'a stale serial is ignored')
        build._flash_reply(quote('builderror|' + quote('Something is in the way')))
        self.assertEqual(build._last_error['text'], 'Something is in the way')
        spoken = []
        with patch.object(core, 'speak', side_effect=lambda text, *a, **k: spoken.append(text)):
            build._flash_reply(quote('selected|0|' + quote('Front Door')))
        self.assertEqual(build._product['name'], 'Front Door')
        self.assertTrue(spoken[-1].startswith('Chosen: Front Door.'))


if __name__ == '__main__':
    unittest.main()
