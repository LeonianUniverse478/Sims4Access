"""Mod menu census: dialogs a mod shows are logged with the calling mod, the
dialog class, raw-text title and rows; EA's own dialogs are not logged;
nothing is spoken; logging off writes nothing."""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env


class Token(object):
    def __init__(self, raw_text='', text_string=None):
        self.raw_text, self.text_string = raw_text, text_string


class LS(object):
    def __init__(self, raw=None, key=0):
        self.hash = key
        self.tokens = [Token(raw)] if raw else []


class Msg(object):
    def __init__(self, title=None, text=None):
        self.title, self.text = title, text

    def HasField(self, name):
        return getattr(self, name) is not None


def make_ui():
    class UiDialog(object):
        def __init__(self, title):
            self.title_ls = title

        def build_msg(self, *args, **kwargs):
            return Msg(title=self.title_ls)

    class UiItemPicker(UiDialog):
        def __init__(self, title, rows):
            UiDialog.__init__(self, title)
            self.picker_rows = rows

    return UiDialog, UiItemPicker


# A frame from EA code: compiled with an EA file name.
EA_CALL = compile('def ea_show(dialog):\n    return dialog.build_msg()\n', r'T:\InGame\Gameplay\Scripts\Server\ui\fake.py', 'exec')
MOD_CALL = compile('def mod_show(dialog):\n    return ea_show(dialog)\n', r'C:\mods\mc_ui.py', 'exec')


class ModUiTests(unittest.TestCase):
    def setUp(self):
        self.UiDialog, self.UiItemPicker = make_ui()
        self.lines, self.spoken = [], []
        modules = {'ui': types.ModuleType('ui'), 'ui.ui_dialog': types.SimpleNamespace(UiDialog=self.UiDialog)}
        for item in (patch.dict(sys.modules, modules),
                     patch.object(env.speech, 'log_line', side_effect=self.lines.append),
                     patch.object(env.speech, 'speak', side_effect=lambda *a, **k: self.spoken.append(a)),
                     patch.object(env.speech, 'log_enabled', True)):
            item.start()
            self.addCleanup(item.stop)
        sys.modules.pop('tyjokr_a11y_modui', None)
        import tyjokr_a11y_modui as modui
        self.modui = modui
        self.addCleanup(sys.modules.pop, 'tyjokr_a11y_modui', None)
        ea = {'__name__': 'ui.fake'}
        exec(EA_CALL, ea)
        mod = {'__name__': 'mc_cmd_center.mc_ui', 'ea_show': ea['ea_show']}
        exec(MOD_CALL, mod)
        self.ea_show, self.mod_show = ea['ea_show'], mod['mod_show']

    def picker(self):
        rows = [types.SimpleNamespace(name=LS('MC Settings')), types.SimpleNamespace(name=LS(key=0x1234ABCD))]
        return self.UiItemPicker(LS('MC Command Center'), rows)

    def test_mod_dialog_is_logged_with_its_source(self):
        msg = self.mod_show(self.picker())
        self.assertEqual(ls_title(msg), 'MC Command Center')
        line = [l for l in self.lines if l.startswith('modui: mc_cmd_center')][0]
        self.assertIn(r'(C:\mods\mc_ui.py) UiItemPicker title "MC Command Center"', line)
        self.assertIn('rows 2: "MC Settings" | "key 0x1234ABCD"', line)
        self.assertEqual(self.spoken, [])

    def test_ea_dialogs_and_logging_off_are_silent(self):
        # In the game every frame above EA's dialog code is EA's too; here the
        # test runner sits above it, so treat the runner and this file as EA.
        import os
        runner = (os.path.dirname(os.__file__), os.path.basename(__file__), __file__)
        with patch.object(self.modui, 'EA_PREFIXES', self.modui.EA_PREFIXES + runner):
            self.ea_show(self.picker())
        self.assertEqual(self.lines, [])
        with patch.object(env.speech, 'log_enabled', False):
            self.mod_show(self.picker())
        self.assertEqual(self.lines, [])

    def test_installed_once_and_loaded_at_startup(self):
        wrapped = self.UiDialog.build_msg
        self.modui.install()
        self.assertIs(self.UiDialog.build_msg, wrapped)
        with open(env.ROOT / 'Scripts' / 'tyjokr_a11y_keys.py', encoding='utf-8') as handle:
            self.assertIn('import tyjokr_a11y_modui', handle.read())


def ls_title(msg):
    return msg.title.tokens[0].raw_text


if __name__ == '__main__':
    unittest.main()
