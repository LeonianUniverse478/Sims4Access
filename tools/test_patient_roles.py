"""Get to Work hospital: the scanner says which Sims are patients and where
they are in their visit (PatientSituationBase's current state class)."""
import sys
import types
import unittest
from unittest.mock import patch

import test_feedback_v9 as fixture  # noqa: F401  (loads the offline game mocks)
import tyjokr_a11y_lang as lang
import tyjokr_a11y_scanner as scanner


class PatientSituationBase(object):
    def __init__(self, patient, state):
        self._patient = patient
        self._cur_state = state

    def get_patient(self):
        return self._patient


def state(name):
    return type(name, (object,), {})()


class PatientRoleTests(unittest.TestCase):
    def setUp(self):
        self.mateo = types.SimpleNamespace(id=11)
        self.tala = types.SimpleNamespace(id=12)
        situations = [PatientSituationBase(self.mateo, state('_AdmittedState')),
                      PatientSituationBase(self.tala, state('WaitingState')),
                      PatientSituationBase(None, state('ArrivingState')),
                      types.SimpleNamespace(get_patient=lambda: self.mateo)]
        manager = types.SimpleNamespace(values=lambda: situations)
        modules = {
            'services': types.SimpleNamespace(get_zone_situation_manager=lambda: manager),
            'situations': types.ModuleType('situations'),
            'situations.complex': types.ModuleType('situations.complex'),
            'situations.complex.patient_situation_base':
                types.SimpleNamespace(PatientSituationBase=PatientSituationBase),
        }
        for item in (patch.dict(sys.modules, modules), patch.object(lang, '_locale_lang', 'en')):
            item.start()
            self.addCleanup(item.stop)

    def test_patients_by_stage(self):
        self.assertEqual(scanner._patient_roles(), {11: 'patient, admitted', 12: 'patient, waiting'})

    def test_unknown_stage_is_still_a_patient(self):
        situation = PatientSituationBase(types.SimpleNamespace(id=13), state('SomeNewState'))
        manager = types.SimpleNamespace(values=lambda: [situation])
        with patch.dict(sys.modules, {'services': types.SimpleNamespace(get_zone_situation_manager=lambda: manager)}):
            self.assertEqual(scanner._patient_roles(), {13: 'patient'})

    def test_no_situation_manager(self):
        with patch.dict(sys.modules, {'services': types.SimpleNamespace(get_zone_situation_manager=lambda: None)}):
            self.assertEqual(scanner._patient_roles(), {})

    def test_role_is_spoken_after_the_name(self):
        entry = scanner.Entry(11, True, 'Mateo Lewis', 0, 20, 3, 0, 'SIMS', 'SIMS')
        entry.availability = 'ready'
        entry.role = 'patient, waiting'
        parts = scanner._entry_parts(entry, 4, 11)
        self.assertEqual(parts[0], 'Mateo Lewis')
        self.assertTrue(parts[1].startswith(', patient, waiting, 20 '))
        entry.role = ''
        self.assertTrue(scanner._entry_parts(entry, 4, 11)[1].startswith(', 20 '))


if __name__ == '__main__':
    unittest.main()
