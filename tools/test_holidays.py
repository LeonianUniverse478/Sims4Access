"""Holiday announcements (2026-11-12): a game notification when a holiday
starts for the active household, and once after loading a save on one.
EA's HolidayTracker, holiday service and notification are stand-ins here."""
from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Scripts'))

shown = []


class LocalizedString(object):
    def __init__(self, text):
        self.text = text

    def __repr__(self):
        return 'L({!r})'.format(self.text)


class Loc(object):
    @staticmethod
    def get_raw_text(text):
        return LocalizedString(text)

    @staticmethod
    def get_comma_separated_list(*items):
        return LocalizedString(', '.join(i.text for i in items))

    @staticmethod
    def get_name_value_pair(name, value):
        return LocalizedString('{}: {}'.format(name.text, value.text))

    @staticmethod
    def get_new_line_separated_strings(*items):
        return LocalizedString('\n'.join(i.text for i in items))


class HolidayTracker(object):
    def __init__(self, owner):
        self._owner = owner
        self.active_holiday_id = None

    def activate_holiday(self, holiday_id, from_load=False):
        self.active_holiday_id = holiday_id


class Zone(object):
    def on_loading_screen_animation_finished(self, *args, **kwargs):
        return 'loaded'


class Notification(object):
    @staticmethod
    def TunableFactory():
        class Factory(object):
            @staticmethod
            def default(owner, text, title):
                return types.SimpleNamespace(show_dialog=lambda: shown.append((title().text, text().text)))
        return Factory()


def tradition(name, description=None):
    return types.SimpleNamespace(_display_data=types.SimpleNamespace(
        instance_display_name=LocalizedString(name),
        instance_display_description=LocalizedString(description) if description else None))


class Service(object):
    def get_holiday_display_name(self, holiday_id):
        return LocalizedString('Winterfest')

    def get_holiday_traditions(self, holiday_id):
        return [tradition('Decorate', 'Put up decorations.'), tradition('Open Presents')]

    def get_holiday_time_off_work(self, holiday_id):
        return True

    def get_holiday_time_off_school(self, holiday_id):
        return True


active = types.SimpleNamespace()
other = types.SimpleNamespace()
services = types.ModuleType('services')
services.holiday_service = lambda: Service()
services.active_household = lambda: active
services.active_sim_info = lambda: None
localization = types.ModuleType('sims4.localization')
localization.LocalizedString = LocalizedString
localization.LocalizationHelperTuning = Loc
sims4 = types.ModuleType('sims4')
sims4.localization = localization
tracker_mod = types.ModuleType('holidays.holiday_tracker')
tracker_mod.HolidayTracker = HolidayTracker
zone = types.ModuleType('zone')
zone.Zone = Zone
notification = types.ModuleType('ui.ui_dialog_notification')
notification.UiDialogNotification = Notification
speech = types.ModuleType('tyjokr_a11y_speech')
speech.log_line = lambda line: None
sys.modules.update({'services': services, 'sims4': sims4, 'sims4.localization': localization,
                    'holidays': types.ModuleType('holidays'), 'holidays.holiday_tracker': tracker_mod,
                    'zone': zone, 'ui': types.ModuleType('ui'), 'ui.ui_dialog_notification': notification,
                    'tyjokr_a11y_speech': speech})

import tyjokr_a11y_holidays as holidays  # noqa: E402

EXPECTED = ('Winterfest', 'Today is a holiday.\nTraditions:\nDecorate: Put up decorations.\nOpen Presents\nNo work or school today.')


class HolidayTests(unittest.TestCase):
    def setUp(self):
        del shown[:]
        del holidays._pending_load[:]

    def test_a_holiday_starting_is_announced(self):
        HolidayTracker(active).activate_holiday(5)
        self.assertEqual(shown, [EXPECTED])

    def test_other_households_are_quiet(self):
        HolidayTracker(other).activate_holiday(5)
        self.assertEqual(shown, [])

    def test_a_holiday_running_at_load_is_announced_after_loading(self):
        tracker = HolidayTracker(active)
        active.holiday_tracker = tracker
        tracker.activate_holiday(5, from_load=True)
        self.assertEqual(shown, [], 'not during the loading screen')
        self.assertEqual(Zone().on_loading_screen_animation_finished(), 'loaded')
        self.assertEqual(shown, [EXPECTED], 'once, after it')
        Zone().on_loading_screen_animation_finished()
        self.assertEqual(len(shown), 2, 'each load of a holiday day says it again')
        tracker.active_holiday_id = None
        Zone().on_loading_screen_animation_finished()
        self.assertEqual(len(shown), 2, 'no holiday, nothing said')

    def test_wrapped_once(self):
        self.assertTrue(HolidayTracker.activate_holiday._a11y_wrapped)
        holidays._install()
        HolidayTracker(active).activate_holiday(5)
        self.assertEqual(len(shown), 1)


if __name__ == '__main__':
    unittest.main()
