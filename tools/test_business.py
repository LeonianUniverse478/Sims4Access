"""The accessibility menu's Businesses row: every business the household owns
through EA's business system (retail stores, mod businesses such as the
WickedWhims strip club), read from BusinessManager with the figures the
owned-business panel shows; plus and minus are spoken for signed amounts."""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_business as business
import tyjokr_a11y_hub as hub
import tyjokr_a11y_narrator as narrator

lang = env.lang


class Manager(object):
    def __init__(self, zone, is_open=True, profit=1500, employees_ok=True):
        self.business_zone_id = zone
        self.is_open = is_open
        self.funds = types.SimpleNamespace(money=24500)
        self.daily_items_sold = 7
        self._customer_manager = types.SimpleNamespace(session_customers_served=5)
        self.daily_revenue = 2100
        self.markup_multiplier = 1.25
        self.employee_count = 2
        self.profit = profit
        self.employees_ok = employees_ok

    def get_star_rating(self):
        return 3.5

    def get_daily_outgoing_costs(self, include_employee_wages=True):
        assert include_employee_wages is False
        return 600

    def get_daily_net_profit(self, include_employee_wages=True):
        assert include_employee_wages is False
        return self.profit

    def get_total_employee_wages_per_hour(self):
        return 40

    def meets_minimum_employee_requirment(self):
        return self.employees_ok


class BusinessTests(unittest.TestCase):
    def setUp(self):
        self.spoken, self.windows, self.ui = [], [], []
        self.managers = {11: Manager(11), 12: Manager(12, is_open=False, profit=-300, employees_ok=False)}
        names = {11: 'Fields Boutique', 12: 'Velvet Pole Club'}
        services = types.SimpleNamespace(
            active_household=lambda: types.SimpleNamespace(id=1),
            business_service=lambda: types.SimpleNamespace(get_business_managers_for_household=lambda hid: self.managers),
            get_persistence_service=lambda: types.SimpleNamespace(
                get_zone_proto_buff=lambda zone: types.SimpleNamespace(name=names.get(zone, ''))))
        for item in (patch.dict(sys.modules, {'services': services}),
                     patch.object(env.speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text)),
                     patch.object(business.menu, '_raw', side_effect=lambda text: text),
                     patch.object(hub.menu, '_raw', side_effect=lambda text: text),
                     patch.object(hub, '_ui', side_effect=self.ui.append),
                     patch.object(hub, '_window', side_effect=lambda title, text, rows, localized_title=None:
                                  self.windows.append((title, rows)) or True),
                     patch.object(lang, '_locale_lang', 'en')):
            item.start()
            self.addCleanup(item.stop)

    def test_menu_row(self):
        hub.open_hub()
        labels = [row[0] for row in self.windows[-1][1]]
        self.assertEqual(labels.index(lang.t('events')) + 1, labels.index(lang.t('businesses')))

    def test_each_business_reads_the_panel_figures(self):
        self.assertTrue(business.businesses_window())
        rows = self.windows[-1][1]
        self.assertEqual([row[0] for row in rows], ['Fields Boutique', 'Velvet Pole Club'])
        self.assertEqual(rows[0][1], 'Open. 3.5 stars. Business funds: 24,500 simoleons. '
                                     'Today: 7 items sold, 5 customers served, revenue 2,100 simoleons, '
                                     'outgoing costs 600 simoleons, net profit 1,500 simoleons. '
                                     'Markup 25 percent. Employees: 2, wages 40 simoleons per hour.')
        self.assertIn('Closed.', rows[1][1])
        self.assertIn('net profit minus 300 simoleons', rows[1][1])
        self.assertTrue(rows[1][1].endswith('Not enough employees to open.'))

    def test_enter_opens_the_business_panel(self):
        business.businesses_window()
        self.windows[-1][1][0][2]()
        self.assertEqual(self.ui, ['OpenHouseholdInfoVenuePanel'])

    def test_no_businesses(self):
        self.managers.clear()
        self.assertFalse(business.businesses_window())
        self.assertEqual(self.spoken, ['Your household does not own a business.'])

    def test_one_broken_business_does_not_hide_the_others(self):
        broken = Manager(13)
        broken.get_daily_net_profit = None
        self.managers[13] = broken
        business.businesses_window()
        self.assertEqual(len(self.windows[-1][1]), 3)

    def test_signed_amounts_say_plus_and_minus(self):
        self.assertEqual(narrator._clean_glyphs('-  §500'), 'minus 500 simoleons')
        self.assertEqual(narrator._clean_glyphs('+  §1,200'), 'plus 1,200 simoleons')
        self.assertEqual(narrator._clean_glyphs('Self-Employed §500'), 'Self-Employed 500 simoleons')


if __name__ == '__main__':
    unittest.main()
