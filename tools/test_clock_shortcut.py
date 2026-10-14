"""Control Alt C and the accessibility menu row ask the client for its own
clock text (UI message A11yClock); a11y.clock_enc carries the localized
answer as 'clock:<text>' or an empty text that is spoken as unavailable.
No numeric weekday fallback and no silence; the pointer path
(a11y.timewidget_enc) is separate so a hover never passes for the reply.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_hub as hub
import tyjokr_a11y_narrator as narrator
import tyjokr_a11y_shortcuts as shortcuts

keys = env.keys
lang = env.lang


class ClockTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.queue.clear()
        env.messages.clear()
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        keys._blocking_explicit = None
        self.spoken = []
        speech = patch.object(env.speech, 'speak',
                              side_effect=lambda text, *args, **kwargs: self.spoken.append(text))
        speech.start()
        self.addCleanup(speech.stop)
        locale = patch.object(lang, '_locale_lang', 'en')
        locale.start()
        self.addCleanup(locale.stop)

    def test_c_is_the_clock_chord_and_is_described(self):
        self.assertEqual(keys.CHORDS[0x43], ('clock', False))
        self.assertEqual(keys.CHORD_NAMES[0x43], 'C')
        self.assertIn('day and time', shortcuts.chord_label('clock'))
        rows = shortcuts.sections(numpad=False)[1][1]
        self.assertTrue(any(row.startswith('Control + Alt + C:') for row in rows), rows)

    def test_the_chord_asks_the_client_in_the_world_and_behind_owners(self):
        keys._chord('clock')
        env.drain()
        self.assertEqual(env.messages, ['A11yClock'])
        env.messages.clear()
        keys.apply_modal_state('101', 'context')     # a dialog does not change the clock
        keys._chord('clock')
        env.drain()
        self.assertEqual(env.messages, ['A11yClock'])
        self.assertEqual(self.spoken, [])            # the reply speaks, not the request

    def test_typing_owns_the_key(self):
        for state in ('01', '11'):
            keys.apply_modal_state(state, 'modalstate')
            keys._chord('clock')
            env.drain()
        self.assertEqual(env.messages, [])

    def test_the_reply_is_spoken_verbatim_without_the_prefix(self):
        narrator.a11y_clock_enc('clock%3ASun%208%3A05%20AM.%20Paused')
        self.assertEqual(self.spoken, ['Sun 8:05 AM. Paused'])

    def test_an_empty_reply_says_unavailable_in_words(self):
        for payload in ('clock%3A', '', 'clock%3A%20%20'):
            self.spoken.clear()
            narrator.a11y_clock_enc(payload)
            self.assertEqual(self.spoken, [lang.t('clock unavailable')], payload)
        self.assertNotEqual(lang.t('clock unavailable'), 'clock unavailable')
        self.assertNotIn('day 1', lang.t('clock unavailable').lower())

    def test_the_hub_offers_day_and_time_after_household_funds(self):
        seen = []
        with patch.object(hub, '_window', side_effect=lambda title, text, rows: seen.append(rows)), \
                patch.object(hub.menu, '_raw', side_effect=lambda text: text):
            hub.open_hub()
        labels = [row[0] for row in seen[0]]
        self.assertIn(lang.t('day and time'), labels)
        self.assertEqual(labels.index(lang.t('day and time')),
                         labels.index(lang.t('household funds')) + 1)
        callback = seen[0][labels.index(lang.t('day and time'))][2]
        self.assertTrue(callback())
        env.drain()
        self.assertEqual(env.messages, ['A11yClock'])

    def test_household_funds_follow_the_clock(self):
        household = types.SimpleNamespace(funds=types.SimpleNamespace(money=12345))
        services = types.SimpleNamespace(active_household=lambda: household)
        with patch.dict(sys.modules, {'services': services}):
            narrator.a11y_clock_enc('clock%3ASun%208%3A05%20AM.%20Paused')
            narrator.a11y_clock_enc('clock%3A')
        self.assertEqual(self.spoken, [
            'Sun 8:05 AM. Paused. Household funds: 12,345 simoleons',
            lang.t('clock unavailable') + ' Household funds: 12,345 simoleons'])

    def test_no_household_reads_the_clock_alone(self):
        services = types.SimpleNamespace(active_household=lambda: None)
        with patch.dict(sys.modules, {'services': services}):
            narrator.a11y_clock_enc('clock%3ASun%208%3A05%20AM')
        broken = types.SimpleNamespace(active_household=lambda: 1 / 0)
        with patch.dict(sys.modules, {'services': broken}):
            narrator.a11y_clock_enc('clock%3ASun%208%3A05%20AM')
        self.assertEqual(self.spoken, ['Sun 8:05 AM', 'Sun 8:05 AM'])

    def test_terms_exist_in_english_and_polish_without_dashes(self):
        for term in ('day and time', 'clock unavailable'):
            entry = lang._TRANSLATIONS[term]
            self.assertIn('en', entry)
            self.assertIn('pl', entry)
            for text in entry.values():
                self.assertNotIn(chr(0x2014), text)
                self.assertNotIn(chr(0x2013), text)


if __name__ == '__main__':
    unittest.main(verbosity=2)
