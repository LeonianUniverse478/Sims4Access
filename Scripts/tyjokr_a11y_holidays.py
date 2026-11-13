"""Holiday announcements (Seasons). Leo, 2026-11-12: when a day is a
holiday of any sort, say so, with its traditions, so players know what to do.

Every holiday, built in or custom, starts for a household through EA's
HolidayTracker.activate_holiday(self, holiday_id, from_load) (holidays/
holiday_tracker.py, 1.129.39 bytecode); self._owner is the household. The
name, traditions and days off come from services.holiday_service():
get_holiday_display_name, get_holiday_traditions (tradition classes, each
with _display_data.instance_display_name), get_holiday_time_off_work and
get_holiday_time_off_school.

The announcement is a game notification, which the notification reader
speaks (and the game localizes custom holiday names itself). A holiday that
is already running when a save loads is announced once the loading screen
is gone. Without Seasons there is no holiday service and nothing happens.
"""
import tyjokr_a11y_speech as speech

_pending_load = []      # holiday ids active at load, announced after it


def _log(message):
    speech.log_line('holidays: ' + message)


def _text(value):
    """A tuned display string: some are factories that must be called."""
    if value is None:
        return None
    try:
        from sims4.localization import LocalizedString
        if isinstance(value, LocalizedString):
            return value
    except Exception:
        pass
    try:
        return value() if callable(value) else value
    except Exception:
        return None


def _message(holiday_id):
    """(title, text) LocalizedStrings for a holiday, or None."""
    import services
    from sims4.localization import LocalizationHelperTuning as Loc
    service = services.holiday_service()
    if service is None:
        return None
    title = _text(service.get_holiday_display_name(holiday_id))
    if title is None:
        return None
    lines = [Loc.get_raw_text('Today is a holiday.')]
    # Each tradition on its own line, with its description: that is what
    # tells the player what to have their Sims do (custom traditions too).
    traditions = []
    for tradition in service.get_holiday_traditions(holiday_id) or ():
        try:
            data = tradition._display_data
            name = _text(data.instance_display_name)
            description = _text(getattr(data, 'instance_display_description', None))
        except Exception:
            name = description = None
        if name is None:
            continue
        traditions.append(Loc.get_name_value_pair(name, description) if description is not None else name)
    if traditions:
        lines.append(Loc.get_raw_text('Traditions:'))
        lines.extend(traditions)
    off = []
    try:
        if service.get_holiday_time_off_work(holiday_id):
            off.append('work')
        if service.get_holiday_time_off_school(holiday_id):
            off.append('school')
    except Exception as ex:
        _log('time off lookup failed: {!r}'.format(ex))
    if off:
        lines.append(Loc.get_raw_text('No {} today.'.format(' or '.join(off))))
    return title, Loc.get_new_line_separated_strings(*lines)


def announce(holiday_id):
    """Show the holiday notification. Simulation thread."""
    try:
        import services
        from ui.ui_dialog_notification import UiDialogNotification
        message = _message(holiday_id)
        if message is None:
            return False
        title, text = message
        dialog = UiDialogNotification.TunableFactory().default(
            services.active_sim_info(), text=lambda *a, **k: text, title=lambda *a, **k: title)
        dialog.show_dialog()
        _log('announced holiday {}'.format(holiday_id))
        return True
    except Exception as ex:
        _log('announcement failed for {}: {!r}'.format(holiday_id, ex))
        return False


def _is_active_household(tracker):
    try:
        import services
        household = services.active_household()
        return household is not None and getattr(tracker, '_owner', None) is household
    except Exception:
        return False


def _install():
    from holidays.holiday_tracker import HolidayTracker
    original = HolidayTracker.activate_holiday
    if getattr(original, '_a11y_wrapped', False):
        return

    def a11y_activate_holiday(self, holiday_id, *args, **kwargs):
        result = original(self, holiday_id, *args, **kwargs)
        try:
            if _is_active_household(self):
                from_load = kwargs.get('from_load', args[0] if args else False)
                if from_load:
                    _pending_load.append(holiday_id)
                else:
                    announce(holiday_id)
        except Exception as ex:
            _log('activate hook failed: {!r}'.format(ex))
        return result

    a11y_activate_holiday._a11y_wrapped = True
    HolidayTracker.activate_holiday = a11y_activate_holiday

    import zone
    loaded = zone.Zone.on_loading_screen_animation_finished

    def a11y_holidays_on_loading_screen_animation_finished(self, *args, **kwargs):
        result = loaded(self, *args, **kwargs)
        try:
            # Also catches a holiday already running in a save: the tracker
            # may have been loaded before the household became active.
            import services
            household = services.active_household()
            tracker = household.holiday_tracker if household is not None else None
            active = tracker.active_holiday_id if tracker is not None else None
            if active is not None and active not in _pending_load:
                _pending_load.append(active)
            for holiday_id in list(dict.fromkeys(_pending_load)):
                if active is None or holiday_id == active:
                    announce(holiday_id)
        except Exception as ex:
            _log('load announcement failed: {!r}'.format(ex))
        finally:
            del _pending_load[:]
        return result

    zone.Zone.on_loading_screen_animation_finished = a11y_holidays_on_loading_screen_animation_finished
    _log('holiday announcements installed')


try:
    _install()
except Exception as _ex:
    _log('not installed: {!r}'.format(_ex))
