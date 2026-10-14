"""Catalog tree (2026-10-14): Ctrl+Alt+O opens EA's Buy catalog as native
pickers (Search, By room, By function, then subcategories, then items), Enter
picks an item up through the Plus catalog bridge, Escape goes back one level,
and Ctrl+Alt+D searches. The tree table is generated from EA's
BuildBuyNavigation movie (tools/gen_catalog_tree.py)."""
import unittest
from unittest.mock import patch
from urllib.parse import quote, unquote

import test_scanner_v5 as env  # noqa: F401  (installs the game stand-ins)
import tyjokr_a11y_catalog as catalog
import tyjokr_a11y_catalogtree as tree
import tyjokr_a11y_keys as keys
import tyjokr_a11y_plus_build as build
import tyjokr_a11y_plus_core as core


class Ui(object):
    """Records pickers, text boxes, speech and bridge messages."""

    def __init__(self, test, building=True):
        self.pickers, self.said, self.sent, self.asked = [], [], [], []
        test.addCleanup(patch.stopall)
        patch.object(core, 'choose', side_effect=self.choose).start()
        patch.object(core, 'ask_text', side_effect=lambda title, text, initial, done: self.asked.append((title, done)) or True).start()
        patch.object(core, 'speak', side_effect=lambda text, interrupt=True: self.said.append(text)).start()
        patch.object(core, 'post', side_effect=lambda fn, *a: fn(*a)).start()
        patch.object(build, 'in_build_mode', return_value=building).start()
        patch.object(build, '_send_ui', side_effect=self.sent.append).start()
        patch.object(catalog, '_label', side_effect=lambda key: 'L%08X' % key).start()
        self.timers = []
        patch.object(catalog.threading, 'Timer', side_effect=lambda delay, fn: self._timer(fn)).start()

    def _timer(self, fn):
        self.timers.append(fn)

        class T(object):
            def start(self):
                pass
        return T()

    def choose(self, title, text, rows, on_pick, tag='main', on_cancel=None, **kw):
        self.pickers.append(dict(title=title, text=text, rows=list(rows), pick=on_pick, cancel=on_cancel, tag=tag))
        return True

    @property
    def last(self):
        return self.pickers[-1]

    def labels(self):
        return [r[0] for r in self.last['rows']]

    def pick(self, label):
        for row in self.last['rows']:
            if row[0] == label:
                return self.last['pick'](row[2])
        raise AssertionError('%s not in %s' % (label, self.labels()))

    def reply(self, items):
        """The bridge answering the last browse request, in 25-item pages."""
        serial = self.sent[-1].split('|')[6]
        for start in range(0, len(items), 25):
            page = '^'.join(quote(n) + '~%d~%d' % (p, c) for (n, p, c) in items[start:start + 25])
            build._flash_reply(quote('cat|%s|%d|%d|%s' % (serial, start, len(items), page)))
        build._flash_reply(quote('catend|%s|%d' % (serial, len(items))))


class CatalogTests(unittest.TestCase):
    def test_tree_is_eas_buy_panel(self):
        self.assertEqual(len(tree.ROOMS), 8)
        self.assertEqual(len(tree.FUNCTIONS), 13)
        for (label, subs) in tree.ROOMS + tree.FUNCTIONS:
            self.assertTrue(subs)
            for sub in subs:
                self.assertEqual(len(sub), 4)
                self.assertIsInstance(sub[1], int)
                self.assertTrue(sub[2])
        kitchen = dict((s[2], s) for s in tree.ROOMS[0][1])
        self.assertIn('BUYCAT_PA_REFRIGERATOR', kitchen)
        self.assertEqual(sum(len(subs) for (_l, subs) in tree.ROOMS + tree.FUNCTIONS), 174)

    def test_chords(self):
        self.assertEqual(keys.CHORDS[0x4F], ('catalog', False))
        self.assertEqual(keys.CHORDS[0x44], ('catalogfind', False))
        self.assertNotIn(0x4E, keys.CHORDS, "Ctrl+Alt+N is NVDA's own key")

    def test_needs_build_mode(self):
        ui = Ui(self, building=False)
        self.assertFalse(catalog.open_tree())
        self.assertFalse(catalog.find())
        self.assertEqual(ui.pickers, [])
        self.assertIn('Open Build mode first', ui.said[0])

    def test_room_to_item_to_pick_up(self):
        ui = Ui(self)
        catalog.open_tree()
        self.assertEqual(ui.labels(), ['Search the catalog', 'By room', 'By function'])
        ui.pick('By room')
        self.assertEqual(ui.labels(), ['L%08X' % label for (label, _s) in tree.ROOMS])
        ui.pick('L%08X' % tree.ROOMS[0][0])
        fridge = tree.ROOMS[0][1][0]
        self.assertEqual(ui.last['title'], 'L%08X' % tree.ROOMS[0][0])
        ui.pick('L%08X' % fridge[0])
        self.assertEqual(ui.sent[-1].split('|')[:6], ['A11y', 'plus', 'browse', '2', 'BUYCAT_PA_REFRIGERATOR', ''])
        self.assertEqual(ui.sent[-1].split('|')[7], '')
        items = [('Fridge %d' % i, 1000 + i, 1 + i % 3) for i in range(30)]
        ui.reply(items)
        self.assertEqual(len(ui.last['rows']), 30, 'both pages arrive')
        self.assertEqual(ui.last['rows'][2][:2], ('Fridge 2', '1,002 simoleons, 3 colours'))
        self.assertEqual(ui.last['rows'][0][1], '1,000 simoleons')
        self.assertIn('30 items', ui.last['text'])
        ui.pick('Fridge 2')
        self.assertEqual(ui.sent[-1], 'A11y|plus|select|2')
        build._flash_reply(quote('selected|2|' + quote('Fridge 2')))
        self.assertTrue(ui.said[-1].startswith('Chosen: Fridge 2. Press Ctrl+Alt+B'))
        self.assertTrue(all(p['tag'] == 'catalogtree' for p in ui.pickers))

    def test_escape_goes_back_one_level(self):
        ui = Ui(self)
        catalog.open_tree()
        ui.pick('By function')
        functions = ui.last
        ui.pick('L%08X' % tree.FUNCTIONS[0][0])
        subs = ui.last
        ui.pick(subs['rows'][0][0])
        ui.reply([('Sofa', 500, 1)])
        ui.last['cancel']()
        self.assertEqual(ui.labels(), [r[0] for r in subs['rows']], 'items -> subcategories')
        ui.last['cancel']()
        self.assertEqual(ui.labels(), [r[0] for r in functions['rows']], 'subcategories -> functions')
        ui.last['cancel']()
        self.assertEqual(ui.labels(), ['Search the catalog', 'By room', 'By function'])

    def test_empty_category_goes_back(self):
        ui = Ui(self)
        catalog.open_tree()
        ui.pick('By function')
        ui.pick('L%08X' % tree.FUNCTIONS[-1][0])
        subs = ui.last
        ui.pick(subs['rows'][0][0])
        ui.reply([])
        self.assertIn('nothing here', ui.said[-1])
        self.assertEqual(ui.labels(), [r[0] for r in subs['rows']])

    def test_search(self):
        ui = Ui(self)
        catalog.find()
        (title, done) = ui.asked[-1]
        self.assertEqual(title, 'Search the catalog')
        done('  double bed ')
        parts = ui.sent[-1].split('|')
        self.assertEqual(parts[2:5], ['browse', '2', ''])
        self.assertEqual(unquote(parts[7]), 'double bed')
        ui.reply([('Double Bed', 900, 2)])
        self.assertEqual(ui.last['title'], 'Results for double bed')
        ui.last['cancel']()
        self.assertEqual(ui.labels(), ['Search the catalog', 'By room', 'By function'])
        catalog.search('zzz')
        ui.reply([])
        self.assertIn('Nothing found for zzz', ui.said[-1])
        self.assertEqual(ui.asked[-1][0], 'Search the catalog', 'asks again')
        ui.asked[-1][1]('')
        self.assertEqual(ui.labels(), ['Search the catalog', 'By room', 'By function'], 'empty search returns to the tree')

    def test_search_from_the_tree(self):
        ui = Ui(self)
        catalog.open_tree()
        ui.pick('Search the catalog')
        self.assertEqual(ui.asked[-1][0], 'Search the catalog')

    def test_no_answer(self):
        ui = Ui(self)
        catalog.search('lamp')
        ui.timers[-1]()
        self.assertIn('did not answer', ui.said[-1])
        late = len(ui.pickers)
        ui.reply([('Lamp', 50, 1)])
        self.assertEqual(len(ui.pickers), late, 'a late answer does not open a picker')

    def test_answer_beats_timeout(self):
        ui = Ui(self)
        catalog.search('lamp')
        ui.reply([('Lamp', 50, 1)])
        ui.timers[-1]()
        self.assertFalse(any('did not answer' in s for s in ui.said))

    def test_old_list_reply_is_ignored(self):
        ui = Ui(self)
        catalog.search('lamp')
        old = ui.sent[-1]
        catalog.search('sofa')
        ui.sent.append(old)
        ui.reply([('Lamp', 50, 1)])
        self.assertEqual(ui.pickers, [], 'a reply for an earlier request is dropped')


if __name__ == '__main__':
    unittest.main()
