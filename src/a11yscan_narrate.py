"""Announcing what your Sim is actually doing.

Polled from the existing real-time pump rather than hooked, because the pump
already runs on the simulation thread at a sensible rate and interaction start
paths are numerous and easy to miss.

Two deliberate choices keep this from becoming noise:

  * Narration never interrupts. Scanner announcements cut speech off; this
    queues behind whatever you are already listening to, so browsing a menu is
    not derailed by your Sim picking up a plate.
  * An interaction must survive two consecutive ticks before it is announced.
    Sims churn through short transitional interactions constantly, and
    announcing those makes the game unlistenable.
"""
import a11yscan_dialogs as dialogs
import a11yscan_speech as speech
import a11yscan_world as world

CONFIRM_TICKS = 2

# Interactions the player neither chose nor needs read aloud. Idle loops,
# emotion churn and posture transitions fire constantly and mean nothing.
_SKIP_WORDS = frozenset((
    'idle', 'emotion', 'posture', 'route', 'routing', 'transition', 'ambient',
    'reaction', 'react', 'stand', 'standing', 'walkstyle', 'lookat', 'look',
    'fidget', 'buff', 'relationship', 'autonomy', 'placeholder',
))


def _worth_announcing(interaction):
    """Only announce things a player could have directed themselves."""
    affordance = getattr(interaction, 'affordance', None) or interaction
    try:
        if getattr(affordance, 'allow_user_directed', True) is False:
            return False
        if getattr(affordance, 'debug', False) or getattr(affordance, 'cheat', False):
            return False
    except Exception:
        pass
    raw = getattr(affordance, '__name__', None) or type(affordance).__name__
    try:
        for word in world.prettify(raw).split():
            if word in _SKIP_WORDS:
                return False
    except Exception:
        pass
    return True

_enabled = True
_announced_key = None
_pending_key = None
_pending_count = 0
_last_label = None


def set_enabled(value):
    global _enabled, _announced_key, _pending_key, _pending_count
    _enabled = bool(value)
    _announced_key = None
    _pending_key = None
    _pending_count = 0


def enabled():
    return _enabled


def status():
    return 'on' if _enabled else 'off'


def last_label():
    return _last_label


def _running(sim):
    """The Sim's current super interaction, whichever accessor works."""
    for getter in (lambda: [sim.queue.running],
                   lambda: list(sim.si_state.sis)):
        try:
            items = [item for item in getter() if item is not None]
            if items:
                return items[0]
        except Exception:
            continue
    return None


def label_for(interaction):
    """Real display text where possible, tuning name as a last resort."""
    for getter in (lambda: interaction.get_name(),
                   lambda: interaction.name):
        try:
            text = dialogs.loc_text(getter())
            if text:
                return text
        except Exception:
            continue

    affordance = getattr(interaction, 'affordance', None) or interaction
    try:
        display = getattr(affordance, 'display_name', None)
        if display is not None:
            value = display(interaction.sim) if callable(display) else display
            text = dialogs.loc_text(value)
            if text:
                return text
    except Exception:
        pass

    raw = getattr(affordance, '__name__', None) or type(affordance).__name__
    return world.prettify_interaction(raw)


def tick():
    """Called from the pump. Cheap, and must never raise into the game."""
    global _announced_key, _pending_key, _pending_count, _last_label
    if not _enabled:
        return
    try:
        sim = world.active_sim()
        if sim is None:
            return
        interaction = _running(sim)
        if interaction is None:
            _announced_key = None
            _pending_key = None
            _pending_count = 0
            return

        if not _worth_announcing(interaction):
            return

        key = id(interaction)
        if key == _announced_key:
            return

        if key != _pending_key:
            _pending_key = key
            _pending_count = 1
            return
        _pending_count += 1
        if _pending_count < CONFIRM_TICKS:
            return

        _announced_key = key
        _pending_key = None
        _pending_count = 0

        label = label_for(interaction)
        if not label or label == _last_label:
            return
        _last_label = label
        # Queue behind whatever is being read rather than cutting it off.
        speech.speak(label, interrupt=False)
    except Exception as ex:
        speech.log('narrate tick failed ({!r})'.format(ex))
