"""Unused TextFields that still hold their own instance name ("txtSimName")
are not read, and a control-type prefix is dropped from derived names
("dd Profit Margin" is read as "Profit Margin")."""
import unittest
from unittest.mock import patch

import test_scanner_v5 as env  # noqa: F401  (offline game mocks)
import tyjokr_a11y_narrator as narrator


class PlaceholderNameTests(unittest.TestCase):
    def tearDown(self):
        narrator._cancel_pending_name()

    def test_field_names_are_placeholders(self):
        for text in ('txtSimName', 'txtPay', 'mcContent', 'btnFire', 'ddProfitMargin'):
            self.assertTrue(narrator._is_placeholder(text), text)
        for text in ('iPhone', 'McDonald', 'Txt', 'txt', 'Kim Fields'):
            self.assertFalse(narrator._is_placeholder(text), text)

    def test_empty_employee_slot(self):
        payload = '\x01'.join(['10|5|Current Janitor(s)', '20|5|txtSimName', '20|50|txtPay',
                               '20|90|txtSatisfaction', '30|5|Select a Sim below to hire.'])
        self.assertEqual(narrator._process(payload, 'widget'), 'Current Janitor(s). Select a Sim below to hire.')

    def test_derived_name_prefix(self):
        for raw, spoken in (('ddProfitMargin', 'Profit Margin'),
                            ('BackgroundColorSelector', 'Background Color Selector'),
                            ('btnTransferLeft', 'Transfer Left')):
            with patch.object(narrator.speech, 'request_hush'), patch.object(narrator.threading, 'Timer'):
                narrator.a11y_widgetname_enc(raw)
            self.assertEqual(narrator._pending_name, spoken)


if __name__ == '__main__':
    unittest.main()
