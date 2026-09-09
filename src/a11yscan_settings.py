"""Game settings that live in the simulation rather than in the client.

The Options screen itself is client-side and cannot be read - the same wall as
CAS and the pause menu. But it is one window over several systems, and some of
those are ordinary Python:

  Autonomy   sim.autonomy_component.get_autonomy_state_setting()
             services.autonomy_service().global_autonomy_settings.set_setting()
  Aging      services.get_aging_service(), which keeps the played-household
             option in _played_household_aging_option and the unplayed one in
             _unplayed_aging_enabled

Every setting here is READ BACK from the game before it is announced. A setting
you cannot read is worse than no setting: it tells you what you last asked for
rather than what is true, and those differ the moment anything else changes it.

Graphics, sound, camera and control settings are NOT here. They live in the
client and in Options.ini, which the game rewrites when it exits, so editing it
while the game runs achieves nothing.
"""
import a11yscan_log as logfile

_index = 0
_active = False


def active():
    return _active


# ------------------------------------------------------------------- autonomy

AUTONOMY_ORDER = ('DISABLED', 'LIMITED_ONLY', 'MEDIUM', 'FULL')
AUTONOMY_LABELS = {
    'DISABLED': 'off, Sims only do what you tell them',
    'LIMITED_ONLY': 'limited, essential needs only',
    'MEDIUM': 'medium',
    'FULL': 'full',
}


def _autonomy_enum():
    from autonomy.settings import AutonomyState
    return AutonomyState


def _autonomy_get():
    """The autonomy state the game reports for your Sim."""
    try:
        import a11yscan_world as world
        sim = world.active_sim()
        component = getattr(sim, 'autonomy_component', None)
        if component is None:
            return None
        value = component.get_autonomy_state_setting()
        enum = _autonomy_enum()
        for position, name in enumerate(AUTONOMY_ORDER):
            if value == getattr(enum, name, None):
                return position
    except Exception as ex:
        logfile.write('settings: could not read autonomy ({!r})'.format(ex))
    return None


def _autonomy_set(position):
    try:
        import services
        settings = services.autonomy_service().global_autonomy_settings
    except Exception as ex:
        logfile.fail('settings: no autonomy service ({!r})'.format(ex))
        return False
    value = getattr(_autonomy_enum(), AUTONOMY_ORDER[position])
    # autonomy/settings.py has two settings classes whose set_setting takes its
    # arguments in opposite orders, so try both rather than guess which this is.
    for label, call in (('(value, group)', lambda: settings.set_setting(value, None)),
                        ('(value)', lambda: settings.set_setting(value)),
                        ('(class, value)',
                         lambda: settings.set_setting(_autonomy_enum(), value))):
        try:
            call()
            logfile.ok('settings: autonomy -> {} via {}'.format(
                AUTONOMY_ORDER[position], label))
            return True
        except Exception as ex:
            logfile.write('settings: autonomy {} failed ({!r})'.format(label, ex))
    return False


# ---------------------------------------------------------------------- aging

# Not a simple on/off: the game distinguishes ageing every played household
# from ageing only the one you are in.
AGING_ORDER = ('DISABLED', 'ALL_PLAYED', 'ACTIVE_FAMILY_ONLY')
AGING_LABELS = {
    'DISABLED': 'off',
    'ALL_PLAYED': 'on for every household you play',
    'ACTIVE_FAMILY_ONLY': 'on for this household only',
}


def _aging_service():
    import services
    return services.get_aging_service()


def _aging_enum():
    from sims.aging.aging_service import PlayedHouseholdSimAgingOptions
    return PlayedHouseholdSimAgingOptions


def _aging_get():
    try:
        value = getattr(_aging_service(), '_played_household_aging_option', None)
        if value is None:
            return None
        enum = _aging_enum()
        for position, name in enumerate(AGING_ORDER):
            if value == getattr(enum, name, None):
                return position
    except Exception as ex:
        logfile.write('settings: could not read aging ({!r})'.format(ex))
    return None


def _aging_set(position):
    try:
        value = getattr(_aging_enum(), AGING_ORDER[position])
        _aging_service().set_aging_enabled(value)
        logfile.ok('settings: aging -> {}'.format(AGING_ORDER[position]))
        return True
    except Exception as ex:
        logfile.fail('settings: aging failed ({!r})'.format(ex))
        return False


def _unplayed_get():
    try:
        value = getattr(_aging_service(), '_unplayed_aging_enabled', None)
        if value is None:
            return None
        return 0 if value else 1
    except Exception as ex:
        logfile.write('settings: could not read unplayed aging ({!r})'.format(ex))
        return None


def _unplayed_set(position):
    try:
        _aging_service().set_unplayed_aging_enabled(position == 0)
        logfile.ok('settings: unplayed aging -> {}'.format(
            'on' if position == 0 else 'off'))
        return True
    except Exception as ex:
        logfile.fail('settings: unplayed aging failed ({!r})'.format(ex))
        return False


# ----------------------------------------------------------------- the fields

SETTINGS = (
    {'name': 'Autonomy',
     'values': [AUTONOMY_LABELS[name] for name in AUTONOMY_ORDER],
     'get': _autonomy_get, 'set': _autonomy_set},
    {'name': 'Aging',
     'values': [AGING_LABELS[name] for name in AGING_ORDER],
     'get': _aging_get, 'set': _aging_set},
    {'name': 'Aging for Sims you are not playing',
     'values': ['on', 'off'],
     'get': _unplayed_get, 'set': _unplayed_set},
)


def _current(position):
    """What the game says this setting is, or None if it would not say."""
    try:
        return SETTINGS[position]['get']()
    except Exception:
        return None


def open_settings():
    global _active, _index
    _active = True
    _index = 0
    return ('Game settings. Up and down for each one, left and right to '
            'change it, backspace to close. {}'.format(describe()))


def close_settings():
    global _active
    _active = False
    return 'Settings closed.'


def describe():
    position = _index % len(SETTINGS)
    setting = SETTINGS[position]
    current = _current(position)
    if current is None:
        return '{}: could not read it. The log has the reason.'.format(
            setting['name'])
    return '{}: {}. {} of {}.'.format(
        setting['name'], setting['values'][current],
        position + 1, len(SETTINGS))


def next_setting(step=1):
    global _index
    _index = (_index + step) % len(SETTINGS)
    return describe()


def change(step=1):
    """Left and right change the setting, then read back what actually took."""
    position = _index % len(SETTINGS)
    setting = SETTINGS[position]
    current = _current(position)
    if current is None:
        return '{} cannot be read, so it is not safe to change.'.format(
            setting['name'])
    wanted = (current + step) % len(setting['values'])
    if not setting['set'](wanted):
        return '{} could not be changed. The log has the reason.'.format(
            setting['name'])
    # Confirm against the game rather than trusting the call, so a setting that
    # silently refuses is heard as refused.
    now = _current(position)
    if now is None:
        return '{} was changed, but cannot be read back.'.format(setting['name'])
    if now != wanted:
        logfile.write('settings: {} stayed at {} after asking for {}'.format(
            setting['name'], setting['values'][now], setting['values'][wanted]))
        return '{} would not change, still {}.'.format(
            setting['name'], setting['values'][now])
    return '{}: {}.'.format(setting['name'], setting['values'][now])
