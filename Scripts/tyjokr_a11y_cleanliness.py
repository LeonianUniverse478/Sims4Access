"""Read-only scanner suffixes for native dirt/dust states verified in-game.

Only reads current state values at announcement time. No interaction tests,
state writes, scan refreshes, object filtering or cached dirtiness.
"""
from itertools import islice
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech

_errors_logged = 0


def suffix(entry):
    global _errors_logged
    if entry.is_sim:
        return ''
    try:
        import services
        obj = services.object_manager().get(entry.obj_id)
        component = getattr(obj, 'state_component', None)
        if component is None:
            return ''
        current = {}
        for value in islice(component.values(), 64):
            state_id = getattr(getattr(value, 'state', None), 'guid64', None)
            if state_id in (15129, 15128, 255045):
                current[state_id] = getattr(value, 'guid64', None)
        # DirtyState is the visual state. Prefer it over the linked dirtiness
        # commodity's state when both exist, including transient disagreement.
        dirty = (current[15129] == 15131 if 15129 in current else current.get(15128) == 15133)
        terms = []
        if dirty:
            terms.append(lang.t('scanner dirty'))
        if current.get(255045) == 255050:
            terms.append(lang.t('scanner dusty'))
        return ''.join(', ' + term for term in terms)
    except Exception as exc:
        # A malformed/removed object must not interrupt scanner navigation.
        # Bound failure logging rather than reporting every repeated keypress.
        if _errors_logged < 5:
            _errors_logged += 1
            speech.log_line('cleanliness: state read failed for {}: {}'.format(entry.obj_id, type(exc).__name__))
        return ''
