"""Transfer direction markers from the household and retail transfer panels
are worded from the language table; amounts still become simoleons and an
empty household name becomes 'the other household'."""
import unittest
from unittest.mock import patch

import test_scanner_v5 as env  # noqa: F401  (offline game mocks)
import tyjokr_a11y_lang as lang
import tyjokr_a11y_narrator as narrator

D = '\x02'


class TransferWordingTests(unittest.TestCase):
    def setUp(self):
        item = patch.object(lang, '_locale_lang', 'en')
        item.start()
        self.addCleanup(item.stop)

    def test_funds_button_line(self):
        payload = '\x01'.join(['0|0|' + D + 'dir' + D + 'funds' + D + 'Fields' + D + 'Goth',
                               '10|5|Transfer Funds',
                               '99000|0|' + D + 'dir' + D + 'has' + D + 'Fields' + D + '\u00a712,000',
                               '99999|0|' + D + 'dir' + D + 'has' + D + 'Goth' + D + '\u00a70'])
        self.assertEqual(narrator._process(payload, 'widget'),
                         'Moves the amount from Fields to Goth. Transfer Funds. '
                         'Fields has 12,000 simoleons. Goth has 0 simoleons')

    def test_sims_and_households(self):
        self.assertEqual(narrator._clean_glyphs(D + 'dir' + D + 'sims' + D + 'Fields' + D),
                         'Moves the selected Sims from Fields to the other household')
        self.assertEqual(narrator._process('40|20|Kim Fields\x0199999|0|' + D + 'dir' + D + 'in' + D + 'Fields' + D,
                                           'widget'), 'Kim Fields. In household Fields')

    def test_retail(self):
        self.assertEqual(narrator._clean_glyphs(D + 'dir' + D + 'from' + D + D), 'From')
        self.assertEqual(narrator._clean_glyphs(D + 'dir' + D + 'retail' + D + '\u00a7500' + D + 'Shop' + D + 'Home'),
                         'Transfers 500 simoleons from Shop to Home')

    def test_polish(self):
        with patch.object(lang, '_locale_lang', 'pl'):
            self.assertEqual(narrator._clean_glyphs(D + 'dir' + D + 'funds' + D + 'Fields' + D + 'Goth'),
                             'Przenosi kwotę z: Fields do: Goth')


if __name__ == '__main__':
    unittest.main()
