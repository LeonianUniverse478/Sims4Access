"""Control Alt E and the accessibility menu row read the whole mood panel in
one reply. SimHub's MoodContainer posts a11y.mood_enc records: M opens a
reading, B carries one moodlet with every tooltip field (description
included), E ends it. The order is BuffDisplay.BuffSort's; an empty payload
is spoken as unavailable; stale or partial readings never speak.
"""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import Mock, patch
from urllib.parse import quote

import test_scanner_v5 as env
import tyjokr_a11y_narrator as narrator

keys = env.keys
lang = env.lang
SEP = '\x01'
ROOT = Path(__file__).resolve().parents[1]


def post(*fields):
    narrator.a11y_mood_enc(quote(SEP.join(fields), safe=''))


def buff(seq, index, mood, name, weight='1', boost='0', effect='', bonus='',
         reason='', time='', description=''):
    post('B', seq, str(index), mood, boost, weight, name, effect, bonus, reason, time, description)


class MoodReaderTests(unittest.TestCase):
    def setUp(self):
        env.settings._stored.clear()
        env.queue.clear()
        env.messages.clear()
        keys._enabled = True
        keys._modal_active = False
        keys._editing_active = False
        narrator._mood_reading = None
        self.spoken = []
        speech = patch.object(env.speech, 'speak',
                              side_effect=lambda text, *args, **kwargs: self.spoken.append(text))
        speech.start()
        self.addCleanup(speech.stop)
        locale = patch.object(lang, '_locale_lang', 'en')
        locale.start()
        self.addCleanup(locale.stop)

    def test_the_chord_asks_the_client_and_modals_keep_the_key(self):
        keys._chord('mood')
        env.drain()
        self.assertEqual(env.messages, ['A11yMood'])
        self.assertEqual(self.spoken, [])            # the reply speaks, not the request
        env.messages.clear()
        keys.apply_modal_state('101', 'context')
        keys._chord('mood')
        env.drain()
        self.assertEqual(env.messages, [])

    def test_everything_is_read_in_one_utterance_with_descriptions(self):
        post('M', '1', '2', 'happy', 'Happy', 'This Sim is feeling good.')
        buff('1', 0, 'happy', 'Had a Great Meal', effect='Happy +1', reason='(From Eating a Great Meal)',
             time='3 hours', description='That meal was delicious.')
        buff('1', 1, 'happy', 'Comfortable', effect='Happy +1', reason='(From Sitting on a Comfy Chair)',
             description='This chair is nice.')
        self.assertEqual(self.spoken, [])
        post('E', '1')
        self.assertEqual(self.spoken, [
            'Happy. This Sim is feeling good. '
            'Comfortable. Happy +1. (From Sitting on a Comfy Chair). This chair is nice. '
            'Had a Great Meal. Happy +1. 3 hours. (From Eating a Great Meal). That meal was delicious'])

    def test_order_follows_the_mood_panel(self):
        post('M', '7', '6', 'happy', 'Happy', '')
        buff('7', 0, 'tense', 'Deadline', weight='1')
        buff('7', 1, 'happy', 'Boosted', weight='3', boost='1', bonus='Boosting: Happy')
        buff('7', 2, 'happy', 'Small Joy', weight='1')
        buff('7', 3, 'happy', 'Big Joy', weight='2')
        buff('7', 4, 'angry', 'Insulted', weight='3')
        buff('7', 5, 'tense', 'Loud Noise', weight='1')
        post('E', '7')
        order = [name for name in ('Big Joy', 'Small Joy', 'Boosted', 'Insulted', 'Deadline', 'Loud Noise')]
        text = self.spoken[0]
        self.assertEqual(sorted(order, key=text.index), order, text)
        self.assertIn('Boosted. Boosting: Happy', text)

    def test_empty_reply_and_empty_reading(self):
        narrator.a11y_mood_enc('')
        self.assertEqual(self.spoken, [lang.t('mood unavailable')])
        self.spoken.clear()
        post('M', '2', '0', 'happy', 'Fine', '')
        post('E', '2')
        self.assertEqual(self.spoken, ['Fine. ' + lang.t('no moodlets')])

    def test_stale_records_and_endings_are_ignored(self):
        post('M', '3', '1', 'sad', 'Sad', '')
        buff('2', 0, 'sad', 'Old Reading')
        post('E', '2')
        self.assertEqual(self.spoken, [])
        post('M', '4', '1', 'sad', 'Sad', '')     # a newer request replaces the partial one
        buff('3', 0, 'sad', 'Lost')
        buff('4', 0, 'sad', 'Mourning', description='Grief.')
        post('E', '3')
        post('E', '4')
        self.assertEqual(self.spoken, ['Sad. Mourning. Grief'])
        post('E', '4')                              # a reading speaks once
        self.assertEqual(len(self.spoken), 1)

    def test_markup_is_removed_and_a_truncated_record_keeps_its_fields(self):
        post('M', '5', '1', 'flirty', 'Flirty', '<font color="#fff">Feeling <b>frisky</b></font>')
        post('B', '5', '0', 'flirty', '0', '1', 'Admired', 'Flirty +1', '', '(From a Compliment)', '')
        post('E', '5')
        self.assertEqual(self.spoken, ['Flirty. Feeling frisky. Admired. Flirty +1. (From a Compliment)'])

    def test_malformed_records_do_not_speak_or_raise(self):
        for payload in ('B%01x', 'Z', 'M%011'):
            narrator.a11y_mood_enc(payload)
        self.assertEqual(self.spoken, [])


class MoodStartupTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('mood_startup_subject', ROOT / 'Scripts/tyjokr_a11y_startup.py')
        self.bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bridge)

    def test_the_main_menu_socket_carries_the_reply(self):
        self.assertIn('a11y.mood_enc', self.bridge.CHANNELS)
        self.assertEqual(self.bridge.parse_post('POST|a11y.mood_enc|'), ('a11y.mood_enc', ''))
        source = (ROOT / 'flash/TooltipManager_patched.as').read_text(encoding='utf-8')
        allowed = source.split('var allowed:Array = [', 1)[1].split(']', 1)[0]
        self.assertIn('"a11y.mood_enc"', allowed)

    def test_dispatch_reaches_the_command_handler(self):
        narrator_mock = Mock()
        with patch.dict('sys.modules', {'tyjokr_a11y_narrator': narrator_mock}):
            self.bridge._dispatch('a11y.mood_enc', '')
        narrator_mock.a11y_mood_enc.assert_called_once_with('')


if __name__ == '__main__':
    unittest.main()
