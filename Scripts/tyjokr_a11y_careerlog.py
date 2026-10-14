"""Research log for the Get to Work doctor career (logging only).

Nothing here is spoken and nothing changes the game. With diagnostic logging
on (Ctrl+Alt+L), every cue the game sends about a sick Sim is written to
TS4_Access.log with the prefix "doctor:", so the accessible patient readout
can be built from what a sighted player is actually shown:

- the sickness and its symptoms when they are applied, with each symptom
  buff's presentation fields (vfx, cas_vfx, appearance_modifier, walkstyle,
  audio stings, voice pitch, pushed interactions, visible moodlet);
- SicknessTracker discoveries: symptom, sickness, exam, treatment, rule-out
  and diagnosis progress;
- thought balloons (BalloonRequest.distribute), headlines
  (Headline.send_headline_message) and visual effects (PlayEffect.start and
  start_one_shot) on a sick Sim;
- patient situation state changes (arriving, waiting, admitted, diagnosed,
  treated).

The log names hidden answers (the sickness, correct treatments) on purpose:
it is research data for the developers, never narration.
"""
import tyjokr_a11y_speech as speech

_installed = False


def _name(obj):
    if obj is None:
        return 'None'
    return getattr(obj, '__name__', None) or type(obj).__name__


def _sim_info(target):
    if target is None:
        return None
    return getattr(target, 'sim_info', None) or (target if hasattr(target, 'sickness_tracker') else None)


def _sick(target):
    info = _sim_info(target)
    try:
        return info is not None and info.sickness_tracker is not None and \
            info.sickness_tracker.current_sickness is not None
    except Exception:
        return False


def _who(target):
    info = _sim_info(target)
    if info is None:
        return repr(target)
    return '{} {} ({})'.format(getattr(info, 'first_name', ''), getattr(info, 'last_name', ''),
                               getattr(info, 'sim_id', '?'))


def _log(text):
    if speech.log_enabled:
        speech.log_line('doctor: ' + text)


def _buff_fields(buff):
    parts = []
    for field in ('visible', 'vfx', 'cas_vfx', 'appearance_modifier', 'walkstyle', 'audio_sting_on_add',
                  'voice_pitch_modifier', 'mood_type'):
        value = getattr(buff, field, None)
        if value:
            parts.append('{}={}'.format(field, _short(value)))
    interactions = getattr(buff, 'interactions', None)
    if interactions:
        try:
            names = [_name(a) for a in getattr(interactions, 'interaction_items', ()) or ()]
        except Exception:
            names = []
        parts.append('interactions={}'.format(names or _short(interactions)))
    return ', '.join(parts) or 'no presentation fields'


def _short(value):
    text = _name(value) if isinstance(value, type) else repr(value)
    return text if len(text) <= 160 else text[:157] + '...'


def _describe_symptom(symptom):
    lines = []
    for buff in getattr(symptom, 'associated_buffs', ()) or ():
        lines.append('    buff {}: {}'.format(_name(buff), _buff_fields(buff)))
    for stat in getattr(symptom, 'associated_statistics', ()) or ():
        lines.append('    statistic {}'.format(_name(stat)))
    return lines


def _wrap_method(cls, name, after):
    original = getattr(cls, name)

    def wrapper(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            after(self, args, kwargs)
        except Exception as ex:
            _log('{}.{} log failed: {!r}'.format(cls.__name__, name, ex))
        return result
    wrapper.__name__ = original.__name__
    setattr(cls, name, wrapper)


def _wrap_classmethod(cls, name, after):
    original = getattr(cls, name).__func__

    def wrapper(klass, *args, **kwargs):
        result = original(klass, *args, **kwargs)
        try:
            after(klass, args, kwargs)
        except Exception as ex:
            _log('{}.{} log failed: {!r}'.format(cls.__name__, name, ex))
        return result
    wrapper.__name__ = original.__name__
    setattr(cls, name, classmethod(wrapper))


def _install_sickness():
    from sickness.sickness import Sickness
    from sickness.sickness_tracker import SicknessTracker

    def applied(klass, args, kwargs):
        info = args[0] if args else kwargs.get('sim_info')
        if not speech.log_enabled:
            return
        _log('sickness {} applied to {} (from_load={})'.format(_name(klass), _who(info),
                                                                  kwargs.get('from_load', args[1:2])))
        for symptom in getattr(klass, 'symptoms', ()) or ():
            _log('  symptom {}'.format(_name(symptom)))
            for line in _describe_symptom(symptom):
                _log(line)
        for buff in getattr(klass, 'associated_buffs', ()) or ():
            _log('  sickness buff {}: {}'.format(_name(buff), _buff_fields(buff)))
        stat = getattr(klass, 'diagnosis_stat', None)
        _log('  diagnosis stat {} visible={}'.format(_name(stat), getattr(stat, 'visible', None)))
        try:
            order = [_name(s) for s in klass.get_ordered_symptoms()]
            _log('  discovery order {}'.format(order))
        except Exception:
            pass
        _log('  correct treatments {}'.format([_name(a) for a in getattr(klass, 'correct_treatments', ()) or ()]))
    _wrap_classmethod(Sickness, 'apply_to_sim_info', applied)

    def tracker_event(label):
        def after(tracker, args, kwargs):
            value = args[0] if args else None
            shown = _short(value) if isinstance(value, (int, float)) else _name(value)
            _log('{} {}: {}'.format(_who(getattr(tracker, '_sim_info', None)), label, shown))
        return after
    for method, label in (('discover_symptom', 'symptom discovered'),
                          ('discover_sickness', 'sickness discovered'),
                          ('track_examination', 'exam done'),
                          ('track_treatment', 'treatment done'),
                          ('rule_out_treatment', 'treatment ruled out'),
                          ('record_last_progress', 'diagnosis progress')):
        _wrap_method(SicknessTracker, method, tracker_event(label))


def _install_cues():
    from balloon.balloon_request import BalloonRequest
    from headlines.headline import Headline
    from vfx import PlayEffect

    def balloon(request, args, kwargs):
        sim = request._sim
        if _sick(sim):
            _log('balloon on {}: icon={} overlay={} type={} category_icon={} icon_info={}'.format(
                _who(sim), _short(getattr(request, 'icon', None)), _short(getattr(request, 'overlay', None)),
                getattr(request, 'balloon_type', None), _short(getattr(request, 'category_icon', None)),
                _short(getattr(request, 'icon_info', None))))
    _wrap_method(BalloonRequest, 'distribute', balloon)

    def headline(klass, args, kwargs):
        info = args[0] if args else kwargs.get('sim_info')
        if _sick(info):
            _log('headline {} on {}: value={}'.format(_name(klass), _who(info), args[1:2]))
    _wrap_classmethod(Headline, 'send_headline_message', headline)

    def effect(label):
        def after(play, args, kwargs):
            target = getattr(play, 'target', None)
            if _sick(target):
                _log('vfx {} on {}: {} joint={}'.format(label, _who(target), getattr(play, 'effect_name', '?'),
                                                       getattr(play, 'joint_name', None)))
        return after
    _wrap_method(PlayEffect, 'start', effect('start'))
    _wrap_method(PlayEffect, 'start_one_shot', effect('one shot'))


def _install_patients():
    from situations.complex.patient_situation_base import PatientSituationBase

    def changed(situation, args, kwargs):
        state = args[0] if args else None
        patient = situation.get_patient() if hasattr(situation, 'get_patient') else None
        _log('patient situation {} for {}: state {}'.format(_name(type(situation)), _who(patient),
                                                            _name(type(state)) if state is not None else None))
    _wrap_method(PatientSituationBase, '_change_state', changed)


def install():
    global _installed
    if _installed:
        return True
    _installed = True
    for part in (_install_sickness, _install_cues, _install_patients):
        try:
            part()
        except Exception as ex:
            speech.log_line('doctor: {} unavailable ({!r})'.format(part.__name__, ex))
    return True


try:
    install()
except Exception as _install_ex:
    speech.log_line('doctor: install failed: {!r}'.format(_install_ex))
