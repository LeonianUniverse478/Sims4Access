"""Doctor research log: hooks call the game's original methods first, never
speak, write only while logging is on, and log only cues about sick Sims."""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env


def game_modules():
    class Tracker(object):
        def __init__(self, info, sickness):
            self._sim_info = info
            self.current_sickness = sickness
            self.calls = []

        def discover_symptom(self, symptom):
            self.calls.append(('symptom', symptom))

        def discover_sickness(self):
            self.calls.append(('sickness',))

        def track_examination(self, affordance):
            self.calls.append(('exam', affordance))

        def track_treatment(self, affordance):
            self.calls.append(('treatment', affordance))

        def rule_out_treatment(self, affordance):
            self.calls.append(('rule out', affordance))

        def record_last_progress(self, progress):
            self.calls.append(('progress', progress))


    class Buff(object):
        visible = True
        vfx = 'steam_ears'
        audio_sting_on_add = None

    class Fever(object):
        associated_buffs = (Buff,)
        associated_statistics = ()

    class Sickness(object):
        symptoms = (Fever,)
        associated_buffs = ()
        diagnosis_stat = None
        correct_treatments = ()
        applied = []

        @classmethod
        def apply_to_sim_info(cls, sim_info, from_load=False):
            cls.applied.append(sim_info)

        @classmethod
        def get_ordered_symptoms(cls):
            return list(cls.symptoms)

    class BalloonRequest(object):
        sent = []

        def __init__(self, sim, icon):
            self._sim, self.icon = sim, icon

        def distribute(self):
            self.sent.append(self.icon)

    class Headline(object):
        @classmethod
        def send_headline_message(cls, sim_info, value, icon_modifier=None):
            return 'sent'

    class PlayEffect(object):
        def __init__(self, target, effect_name):
            self.target, self.effect_name, self.joint_name = target, effect_name, None

        def start(self):
            return 'started'

        def start_one_shot(self):
            return 'shot'

    class PatientSituationBase(object):
        def __init__(self, patient):
            self.patient, self.states = patient, []

        def get_patient(self):
            return self.patient

        def _change_state(self, state):
            self.states.append(state)

    mods = {
        'sickness': types.ModuleType('sickness'),
        'sickness.sickness': types.SimpleNamespace(Sickness=Sickness),
        'sickness.sickness_tracker': types.SimpleNamespace(SicknessTracker=Tracker),
        'balloon': types.ModuleType('balloon'),
        'balloon.balloon_request': types.SimpleNamespace(BalloonRequest=BalloonRequest),
        'headlines': types.ModuleType('headlines'),
        'headlines.headline': types.SimpleNamespace(Headline=Headline),
        'vfx': types.SimpleNamespace(PlayEffect=PlayEffect),
        'situations': types.ModuleType('situations'),
        'situations.complex': types.ModuleType('situations.complex'),
        'situations.complex.patient_situation_base': types.SimpleNamespace(PatientSituationBase=PatientSituationBase),
    }
    return mods, locals()


class CareerLogTests(unittest.TestCase):
    def setUp(self):
        self.mods, self.cls = game_modules()
        self.lines, self.spoken = [], []
        for item in (patch.dict(sys.modules, self.mods),
                     patch.object(env.speech, 'log_line', side_effect=self.lines.append),
                     patch.object(env.speech, 'speak', side_effect=lambda *a, **k: self.spoken.append(a)),
                     patch.object(env.speech, 'log_enabled', True)):
            item.start()
            self.addCleanup(item.stop)
        sys.modules.pop('tyjokr_a11y_careerlog', None)
        import tyjokr_a11y_careerlog as careerlog
        self.careerlog = careerlog
        self.patient = types.SimpleNamespace(first_name='Ana', last_name='Lee', sim_id=7)
        self.patient.sickness_tracker = self.cls['Tracker'](self.patient, self.cls['Sickness'])
        self.healthy = types.SimpleNamespace(first_name='Bo', last_name='Kim', sim_id=8,
                                             sickness_tracker=self.cls['Tracker'](None, None))
        self.healthy.sickness_tracker._sim_info = self.healthy

    def tearDown(self):
        sys.modules.pop('tyjokr_a11y_careerlog', None)

    def test_sickness_and_discoveries_are_logged_after_the_original(self):
        sickness = self.cls['Sickness']
        sickness.apply_to_sim_info(self.patient)
        self.assertEqual(sickness.applied, [self.patient])
        tracker = self.patient.sickness_tracker
        tracker.discover_symptom(self.cls['Fever'])
        tracker.record_last_progress(40)
        self.assertEqual(tracker.calls, [('symptom', self.cls['Fever']), ('progress', 40)])
        text = '\n'.join(self.lines)
        self.assertIn('doctor: sickness Sickness applied to Ana Lee (7)', text)
        self.assertIn("buff Buff: visible=True, vfx='steam_ears'", text)
        self.assertIn('doctor: Ana Lee (7) symptom discovered: Fever', text)
        self.assertIn('doctor: Ana Lee (7) diagnosis progress: 40', text)
        self.assertEqual(self.spoken, [])

    def test_cues_only_for_sick_sims(self):
        balloon = self.cls['BalloonRequest']
        balloon(types.SimpleNamespace(sim_info=self.patient), 'icon_fever').distribute()
        balloon(types.SimpleNamespace(sim_info=self.healthy), 'icon_happy').distribute()
        self.assertEqual(balloon.sent, ['icon_fever', 'icon_happy'])
        effect = self.cls['PlayEffect']
        self.assertEqual(effect(types.SimpleNamespace(sim_info=self.patient), 'spots').start(), 'started')
        self.assertEqual(effect(types.SimpleNamespace(sim_info=self.healthy), 'sparkle').start_one_shot(), 'shot')
        self.assertEqual(self.cls['Headline'].send_headline_message(self.patient, 3), 'sent')
        text = '\n'.join(self.lines)
        self.assertIn("balloon on Ana Lee (7): icon='icon_fever'", text)
        self.assertIn('vfx start on Ana Lee (7): spots', text)
        self.assertIn('headline Headline on Ana Lee (7)', text)
        self.assertNotIn('Bo Kim', text)

    def test_patient_states(self):
        situation = self.cls['PatientSituationBase'](types.SimpleNamespace(sim_info=self.patient))
        situation._change_state(types.SimpleNamespace())
        self.assertEqual(len(situation.states), 1)
        self.assertIn('state SimpleNamespace', self.lines[-1])

    def test_silent_when_logging_is_off(self):
        with patch.object(env.speech, 'log_enabled', False):
            self.cls['Sickness'].apply_to_sim_info(self.patient)
            self.patient.sickness_tracker.discover_symptom(self.cls['Fever'])
        self.assertEqual([line for line in self.lines if 'applied' in line or 'discovered' in line], [])

    def test_installed_once_and_loaded_at_startup(self):
        before = self.cls['Tracker'].discover_symptom
        self.careerlog.install()
        self.assertIs(self.cls['Tracker'].discover_symptom, before)
        with open(env.ROOT / 'Scripts' / 'tyjokr_a11y_keys.py', encoding='utf-8') as handle:
            self.assertIn('import tyjokr_a11y_careerlog', handle.read())


if __name__ == '__main__':
    unittest.main()
