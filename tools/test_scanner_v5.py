"""Offline regression checks; no game access, audio, or native keyboard hook.

Run with py -3.7 tools/test_scanner_v5.py.
"""
import ctypes
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))

commands = types.ModuleType('sims4.commands')
commands.Command = lambda *a, **k: lambda fn: fn
commands.CommandType = types.SimpleNamespace(Live=1)
commands.CheatOutput = lambda connection: lambda text: None
sims4 = types.ModuleType('sims4')
sims4.commands = commands
sys.modules.update({'sims4': sims4, 'sims4.commands': commands})

zone = types.ModuleType('zone')
zone.Zone = type('Zone', (), {'on_loading_screen_animation_finished': lambda *a, **k: None})
sys.modules['zone'] = zone
queue = []
messages = []
pump = types.ModuleType('tyjokr_a11y_pump')
pump.post = lambda fn, *args: queue.append((fn, args)) or True
pump.status = lambda: 'test'
sys.modules[pump.__name__] = pump
startup = types.ModuleType('tyjokr_a11y_startup')
startup.send_navigation = lambda message_name: False
sys.modules[startup.__name__] = startup
distributor = types.ModuleType('distributor')
distributor.ops = types.SimpleNamespace(SendUIMessage=lambda name: name)
distributor.system = types.SimpleNamespace(Distributor=types.SimpleNamespace(
    instance=lambda: types.SimpleNamespace(add_op_with_no_owner=messages.append)))
sys.modules.update({'distributor': distributor, 'distributor.ops': distributor.ops,
                    'distributor.system': distributor.system})

import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech
import tyjokr_a11y_lang as lang

# Importing keys normally starts its threads; disable that only for import.
settings._stored['keyboard'] = False
speech.log_enabled = False
import tyjokr_a11y_keys as keys
import tyjokr_a11y_menu as menu


def drain():
    batch = queue[:]
    queue.clear()
    for fn, args in batch:
        fn(*args)


class RegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        settings.PATH = os.path.join(self.tmp.name, 'test.cfg')
        settings._stored.clear()
        queue.clear()
        messages.clear()
        speech._last_text = None
        speech._last_time = 0
        speech._last_source = None
        speech._pending.clear()
        speech.speech_mode = 'hover'
        speech.braille_mode = 'off'
        speech._backend_name = 'test'
        speech._sapi_proc = None
        keys._enabled = True
        menu._visual_id = None
        self.init_patch = patch.object(speech, 'init', lambda: None)
        self.init_patch.start()

    def tearDown(self):
        if speech._pending_timer:
            speech._pending_timer.cancel()
        self.init_patch.stop()
        self.tmp.cleanup()

    def test_caption_default_persistence_and_settings_coverage(self):
        self.assertFalse(settings.get('captions'))
        self.assertNotIn('captions', settings.render_default())
        settings.set('captions', True)
        self.assertTrue(settings.get('captions'))
        settings.reload()
        self.assertFalse(settings.get('captions'))
        # auto_focus is retained only for reading old cfg files; keyboard
        # mode now controls focus as a coherent feature.
        self.assertEqual(set(settings.DEFAULTS) - {'auto_focus'}, {r.key for r in menu._SETTING_ROWS})

    def test_caption_uses_sim_thread_and_roundtrips_unicode_delimiters(self):
        settings.set('captions', True)
        value = 'Sofá | 100% "例子"\n猫 😀. 3 of 12.'
        speech.speak(value, explicit=True)
        self.assertEqual(messages, [])
        self.assertEqual(len(queue), 1)
        drain()
        self.assertEqual(unquote(messages[0][9:]), value)
        self.assertEqual(messages[0].count('|'), 2)
        speech.speak(value, explicit=True)
        self.assertEqual(queue, [])  # duplicate was never narrated

    def test_caption_manual_capture_and_repeat(self):
        settings.set('captions', True)
        speech.speech_mode = 'manual'
        speech.speak('Chair. 3 of 12.')
        self.assertEqual(queue, [])
        speech.repeat_last()
        drain()
        self.assertEqual(unquote(messages[-1][9:]), 'Chair. 3 of 12.')

    def test_caption_pending_keeps_latest_and_strips_duplicate_prefix(self):
        settings.set('captions', True)
        speech._last_accept_time = speech.time.monotonic()
        with patch.object(speech.threading, 'Timer'):
            speech.speak('Old chair', source='widget')
            speech.speak('New sofa', source='widget')
            self.assertEqual(queue, [])
            speech._flush_pending()
        drain()
        self.assertEqual(unquote(messages[-1][9:]), 'New sofa')
        speech.speak('New sofa. Comfortable.', explicit=True)
        drain()
        self.assertEqual(unquote(messages[-1][9:]), 'Comfortable.')

    def test_caption_limit_off_and_missing_pump(self):
        speech.speak('Disabled', explicit=True)
        self.assertEqual(queue, [])
        settings.set('captions', True)
        speech.speak('😀' * 600, explicit=True)
        drain()
        caption = unquote(messages[-1][9:])
        self.assertEqual(len(caption), 480)
        self.assertTrue(caption.endswith('…'))
        speech.speak('Queued before switch off', explicit=True)
        settings.set('captions', False)
        speech.clear_caption()
        drain()
        self.assertEqual(messages[-1], 'A11y|cap|')
        self.assertEqual(len(messages), 2)
        with patch.object(pump, 'post', return_value=False):
            settings.set('captions', True)
            speech.speak('No lot loaded', explicit=True)
        self.assertEqual(len(messages), 2)

    def test_visual_menu_silent_and_numeric_rows_wrap(self):
        with patch.object(menu, '_show_settings_window', return_value=True) as show, \
                patch.object(speech, 'speak') as speak:
            menu._open_menu()
            show.assert_called_once_with()
            menu._close()
            speak.assert_not_called()
        for row in menu._SETTING_ROWS:
            if row.kind != 'number':
                continue
            settings.set(row.key, row.hi)
            with patch.object(speech, 'restart_sapi'), patch.object(speech, 'speak') as speak:
                menu._enter(row)
                self.assertEqual(settings.get(row.key), row.lo)
                menu._enter(row)
                self.assertEqual(settings.get(row.key), row.lo + row.step)
                speak.assert_not_called()

    def test_visual_pick_refresh_cancel_and_stale_reply(self):
        row_index = next(i for i, r in enumerate(menu.ROWS) if r.key == 'captions')
        reply = types.SimpleNamespace(dialog_id=17, accepted=True,
                                      get_result_tags=lambda: [row_index])
        with patch.object(menu, '_show_settings_window') as show:
            menu._visual_id = 18
            menu._on_settings_pick(reply)
            self.assertFalse(settings.get('captions'))
            show.assert_not_called()
            menu._visual_id = 17
            menu._on_settings_pick(reply)
            self.assertTrue(settings.get('captions'))
            show.assert_called_once_with()
            show.reset_mock()
            reply.accepted = False
            menu._visual_id = 17
            menu._on_settings_pick(reply)
            self.assertFalse(menu.is_open())
            show.assert_not_called()

    def test_first_popup_deferred_and_scanner_keys_unchanged(self):
        self.assertNotIn(0x55, keys.CHORDS)
        self.assertNotIn(0x55, keys._SWALLOW_VKS)
        original = {0x26: ('prev', True), 0x28: ('next', True),
                    0x25: ('prevcat', True), 0x27: ('nextcat', True),
                    0x21: ('prevsub', True), 0x22: ('nextsub', True),
                    0x0D: ('open', False), 0x08: ('back', False),
                    0x53: ('rescan', False), 0x57: ('where', False),
                    0x52: ('repeat', False), 0x48: ('help', False),
                    0x50: ('phone', False), 0x45: ('mood', False),
                    0x47: ('wants', False)}
        self.assertEqual({vk: keys.CHORDS[vk] for vk in original}, original)
        self.assertEqual(set(keys.CHORDS) - set(original),
                         {0x42, 0x54, 0xDB, 0xDD, 0x5A, 0x59, 0x46, 0x58,   # 0x58 = X, sell (2026-09-26)
             0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38,   # Ctrl+Alt+1..8 Sim switch (2026-09-24)
             0x20,                                               # Ctrl+Alt+Space scanner mode (2026-09-25)
             0x43,                                               # Ctrl+Alt+C day and time (2026-09-27)
             0x51,                                               # Ctrl+Alt+Q action queue (2026-09-30)
             0x4C,                                               # Ctrl+Alt+L logging on/off (2026-09-30)
             0x56,                                               # Ctrl+Alt+V events (2026-09-30)
             0x4D, 0x4B})                                        # Ctrl+Alt+M milestones, K character values (2026-10-04)
        with patch.object(menu, '_show_settings_window') as show:
            zone.Zone().on_loading_screen_animation_finished()
            show.assert_not_called()
            self.assertEqual(queue, [])
        for text in lang._TRANSLATIONS['scanner help'].values():
            self.assertNotRegex(text, r'[,、，] ?U')

    def test_hook_lifecycle_typing_modifiers_altgr_focus_disable(self):
        # Drive the real hook loop with Win32 shims. No native hook is installed.
        frames = [
            (set(), True, False, True),                         # typing
            ({keys.VK_CONTROL}, True, False, True),             # Ctrl only
            ({keys.VK_MENU}, True, False, True),                # Alt only
            ({keys.VK_CONTROL, keys.VK_MENU}, True, False, True),
            ({keys.VK_MENU}, True, False, True),                # release Ctrl
            ({keys.VK_CONTROL, keys.VK_MENU}, True, True, True), # AltGr
            ({keys.VK_CONTROL, keys.VK_MENU}, False, False, True),
            ({keys.VK_CONTROL, keys.VK_MENU}, True, False, True),
            ({keys.VK_CONTROL, keys.VK_MENU}, True, False, False),
            ({keys.VK_CONTROL, keys.VK_MENU, keys.VK_SHIFT}, True, False, True),
            ({keys.VK_CONTROL, keys.VK_MENU}, True, False, True),
            (set(), True, False, True),
        ]
        step = [-1]
        installs, removals = [], []

        class WinFn:
            def __init__(self, fn):
                self.fn = fn
            def __call__(self, *args):
                return self.fn(*args)

        def install(*args):
            installs.append(step[0])
            return len(installs)

        def sleep(_seconds):
            step[0] += 1
            if step[0] >= len(frames):
                keys._hook_running = False
                step[0] = len(frames) - 1
            keys._enabled = frames[step[0]][3]

        user32 = types.SimpleNamespace(
            SetWindowsHookExW=WinFn(install),
            UnhookWindowsHookEx=WinFn(lambda handle: removals.append(step[0])),
            GetAsyncKeyState=lambda vk: 0x8000 if vk in frames[step[0]][0] else 0,
            PeekMessageW=lambda *args: 0)
        kernel32 = types.SimpleNamespace(GetModuleHandleW=WinFn(lambda *args: 1))
        fake_time = types.SimpleNamespace(sleep=sleep, monotonic=lambda: max(0, step[0]) * 0.005)
        keys._hook_running = True
        keys._hook_handle = None
        with patch.object(ctypes, 'WinDLL', side_effect=lambda name, **kw: user32 if name == 'user32' else kernel32), \
                patch.object(keys, '_hook_callback_factory', return_value=ctypes.c_void_p(1)), \
                patch.object(keys, '_game_is_foreground', side_effect=lambda *args: frames[step[0]][1]), \
                patch.object(keys, '_altgr_pressed', side_effect=lambda *args: frames[step[0]][2]), \
                patch.object(keys, 'time', fake_time):
            keys._hook_loop()
        self.assertEqual(installs, [3, 7, 10])
        self.assertEqual(removals, [4, 8, 11])
        self.assertIsNone(keys._hook_handle)
        self.assertEqual(keys._hook_state, {})


if __name__ == '__main__':
    unittest.main(verbosity=2)
