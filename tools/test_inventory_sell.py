"""Enter on an item of the active Sim's inventory opens the TS4 Access item
menu (a11y.invitem_enc): Item actions replays EA's click (A11yInvItemActions),
Sell one and Sell all (confirmed) send EA's inventory panel sell request
(inventory.sim_inventory_sell_multiple with an item id and count), and
Choose how many opens EA's native sell picker set up as
SellPickerInteraction does, removing what the client's Sell paid for.
Everything is looked up again before selling.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env
import tyjokr_a11y_hub as hub

lang = env.lang


class Inventory(set):
    def __init__(self):
        super().__init__()
        self.destroyed = []

    def __contains__(self, obj):
        return getattr(obj, 'id', None) in {o.id for o in self}

    def try_destroy_object(self, obj, count):
        self.destroyed.append((obj.id, count))
        return True


class Item:
    def __init__(self, obj_id, value, count=1, locked=False, component_block=False):
        self.id = obj_id
        self.current_value = value
        self.count = count
        self.non_deletable_by_user = locked
        self.is_sell_disabled_from_component = lambda: component_block
        self.definition = types.SimpleNamespace(id=900 + obj_id, build_buy_tags=frozenset((5,)))

    def stack_count(self):
        return self.count


class SellRequest:
    def __init__(self):
        self.sim_id = self.currency_type = None
        self.items = types.SimpleNamespace(add=self._add)
        self.added = []

    def _add(self):
        item = types.SimpleNamespace(id=None, count=None)
        self.added.append(item)
        return item


class Dialog:
    def __init__(self, owner, title=None, text=None):
        self.owner, self.title, self.text = owner, title, text
        self.rows, self.listeners, self.shown = [], [], False
        self.accepted = False
        self.ids_and_amounts_and_price = None
        self.source_inventory = None

    def add_row(self, row):
        self.rows.append(row)

    def add_listener(self, listener):
        self.listeners.append(listener)

    def show_dialog(self):
        self.shown = True


class InventorySellTests(unittest.TestCase):
    def setUp(self):
        env.queue.clear()
        env.messages.clear()
        self.spoken, self.windows, self.ui, self.requests, self.dialogs = [], [], [], [], []
        self.inventory = Inventory()
        self.funds = types.SimpleNamespace(money=1000)
        self.sim = types.SimpleNamespace(id=7, inventory_component=self.inventory,
                                         sim_info=types.SimpleNamespace(get_item_sell_price_modifier=lambda obj: 1.5))
        self.objects = {}
        self.region = types.SimpleNamespace(region_currency_bucks_type=0)
        services = types.SimpleNamespace(
            get_active_sim=lambda: self.sim,
            inventory_manager=lambda: types.SimpleNamespace(get=self.objects.get),
            current_region=lambda: self.region,
            active_household=lambda: types.SimpleNamespace(funds=self.funds),
            client_manager=lambda: types.SimpleNamespace(get_first_client=lambda: types.SimpleNamespace(id=3)))

        def sell_multiple(msg, _connection=None):
            request = self.requests[-1]
            self.assertIs(msg, request)                 # the text form of our request
            for item in request.added:
                obj = self.objects[item.id]
                self.funds.money += round(obj.current_value * item.count * 1.5)
                obj.count -= item.count
            self.sold_connection = _connection

        def new_request():
            self.requests.append(SellRequest())
            return self.requests[-1]

        factory = types.SimpleNamespace(default=lambda owner, title=None, text=None:
                                        self.dialogs.append(Dialog(owner, title, text)) or self.dialogs[-1])
        picker = types.SimpleNamespace(UiSellPicker=types.SimpleNamespace(TunableFactory=lambda: factory),
                                       PurchasePickerRow=lambda **kwargs: kwargs)
        modules = {
            'services': services,
            'google': types.SimpleNamespace(), 'google.protobuf': types.SimpleNamespace(),
            'google.protobuf.text_format': types.SimpleNamespace(MessageToString=lambda request: request),
            'protocolbuffers': types.SimpleNamespace(),
            'protocolbuffers.UI_pb2': types.SimpleNamespace(InventorySellRequest=new_request),
            'server_commands': types.SimpleNamespace(),
            'server_commands.inventory_commands': types.SimpleNamespace(sim_inventory_sell_multiple=sell_multiple),
            'sims4.localization': types.SimpleNamespace(LocalizationHelperTuning=types.SimpleNamespace(
                get_object_name=lambda obj: 'Item {}'.format(obj.id))),
            'ui': types.SimpleNamespace(), 'ui.ui_dialog_picker': picker,
        }
        modules['google'].protobuf = modules['google.protobuf']
        modules['google.protobuf'].text_format = modules['google.protobuf.text_format']
        modules['protocolbuffers'].UI_pb2 = modules['protocolbuffers.UI_pb2']
        modules['server_commands'].inventory_commands = modules['server_commands.inventory_commands']
        modules['ui'].ui_dialog_picker = picker
        patches = [patch.dict(sys.modules, modules),
                   patch.object(hub, '_sell_factory', None),
                   patch.object(env.speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text)),
                   patch.object(hub.menu, '_raw', side_effect=lambda text: text),
                   patch.object(hub, '_ui', side_effect=self.ui.append),
                   patch.object(hub, '_window', side_effect=lambda title, text, rows, localized_title=None:
                                self.windows.append((title, text, rows, localized_title)) or True),
                   patch.object(lang, '_locale_lang', 'en')]
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)

    def add(self, item, owned=True):
        self.objects[item.id] = item
        if owned:
            self.inventory.add(item)
        return item

    def rows(self):
        title, text, rows, localized = self.windows[-1]
        return [row[0] for row in rows], dict((row[0], row[2]) for row in rows), localized

    def test_single_item_menu_and_sale(self):
        self.add(Item(1, 20))
        self.assertTrue(hub.a11y_invitem_enc('1'))
        labels, callbacks, title = self.rows()
        self.assertEqual(title, 'Item 1')
        self.assertEqual(labels, ['Item actions', 'Sell for 30 simoleons'])
        self.assertTrue(callbacks['Sell for 30 simoleons']())
        request = self.requests[-1]
        self.assertEqual((request.sim_id, request.currency_type), (7, 0))
        self.assertEqual([(i.id, i.count) for i in request.added], [(1, 1)])
        self.assertEqual(self.funds.money, 1030)
        self.assertEqual(self.sold_connection, 3)
        self.assertEqual(self.spoken, ['Sold for 30 simoleons.'])

    def test_stack_menu_rows_and_item_actions(self):
        self.add(Item(2, 10, count=5))
        hub.a11y_invitem_enc('2')
        labels, callbacks, _title = self.rows()
        self.assertEqual(labels, ['Item actions', 'Sell one for 15 simoleons', 'Sell all 5 for 75 simoleons',
                                  'Choose how many to sell'])
        callbacks['Item actions']()
        self.assertEqual(self.ui, ['A11yInvItemActions'])

    def test_sell_all_asks_first(self):
        self.add(Item(2, 10, count=5))
        hub.a11y_invitem_enc('2')
        self.rows()[1]['Sell all 5 for 75 simoleons']()
        self.assertEqual(self.requests, [])              # nothing sold before the answer
        labels, callbacks, _title = self.rows()
        self.assertEqual(labels, ['Yes, sell all 5 for 75 simoleons', 'No, keep them'])
        callbacks['No, keep them']()
        self.assertEqual((self.requests, self.spoken), ([], [lang.t('nothing sold')]))
        callbacks['Yes, sell all 5 for 75 simoleons']()
        self.assertEqual([(i.id, i.count) for i in self.requests[-1].added], [(2, 5)])

    def test_unsellable_items_get_no_sell_rows(self):
        self.add(Item(3, 10, locked=True))
        self.add(Item(4, 10, component_block=True))
        for obj_id in ('3', '4'):
            hub.a11y_invitem_enc(obj_id)
            self.assertEqual(self.rows()[0], ['Item actions', 'This item cannot be sold.'])

    def test_items_outside_the_sims_inventory_keep_eas_menu(self):
        self.add(Item(5, 10), owned=False)               # an object inventory, not the Sim's
        self.assertFalse(hub.a11y_invitem_enc('5'))
        self.assertEqual((self.windows, self.ui), ([], ['A11yInvItemActions']))
        self.assertFalse(hub.a11y_invitem_enc('not a number'))

    def test_selling_rechecks_the_sim_and_the_item(self):
        item = self.add(Item(6, 10, count=2))
        hub.a11y_invitem_enc('6')
        sell_one = self.rows()[1]['Sell one for 15 simoleons']
        self.sim = types.SimpleNamespace(id=8, inventory_component=self.inventory, sim_info=self.sim.sim_info)
        self.assertFalse(sell_one())
        self.assertEqual(self.spoken, [lang.t('sim unavailable')])
        self.sim.id = 7
        self.inventory.discard(item)
        self.assertFalse(sell_one())
        self.assertEqual(self.spoken[-1], lang.t('item no longer in inventory'))
        self.assertEqual(self.requests, [])

    def test_a_refused_sale_says_so(self):
        self.add(Item(7, 10))
        hub.a11y_invitem_enc('7')
        with patch.dict(sys.modules['server_commands.inventory_commands'].__dict__,
                        {'sim_inventory_sell_multiple': lambda msg, _connection=None: None}):
            self.assertFalse(self.rows()[1]['Sell for 15 simoleons']())
        self.assertEqual(self.spoken, [lang.t('sale failed')])

    def test_sell_window_is_set_up_like_eas_and_removes_what_was_paid(self):
        item = self.add(Item(8, 10, count=6))
        hub.a11y_invitem_enc('8')
        self.rows()[1]['Choose how many to sell']()
        dialog = self.dialogs[-1]
        self.assertTrue(dialog.shown)
        self.assertEqual(dialog.title(), 'Item 8')
        self.assertEqual((dialog.inventory_object_id, dialog.use_dialog_pick_response), (7, False))
        self.assertEqual(dialog.rows, [dict(def_id=908, is_enable=True, num_available=6, tags=frozenset((5,)),
                                            custom_price=15, objects={item})])
        dialog.accepted = True
        dialog.ids_and_amounts_and_price = [8, 4, 15]    # set by sell_picker_response_by_ids
        dialog.source_inventory = self.inventory
        dialog.listeners[0](dialog)
        self.assertEqual(self.inventory.destroyed, [(8, 4)])
        self.assertEqual(self.spoken, ['Sold for 60 simoleons.'])

    def test_sell_window_cancel_or_missing_amounts_removes_nothing(self):
        self.add(Item(9, 10, count=3))
        hub.a11y_invitem_enc('9')
        self.rows()[1]['Choose how many to sell']()
        dialog = self.dialogs[-1]
        dialog.listeners[0](dialog)                      # canceled
        dialog.accepted = True
        dialog.listeners[0](dialog)                      # accepted but nothing paid
        self.assertEqual((self.inventory.destroyed, self.spoken), ([], []))

    def test_other_currencies_are_named(self):
        self.region.region_currency_bucks_type = 99
        bucks = types.SimpleNamespace(BucksType=lambda value: types.SimpleNamespace(name='GalacticCredits'))
        with patch.dict(sys.modules, {'bucks': types.SimpleNamespace(bucks_enums=bucks), 'bucks.bucks_enums': bucks}):
            self.add(Item(10, 10))
            hub.a11y_invitem_enc('10')
        self.assertEqual(self.rows()[0][1], 'Sell for 15 ' + lang.t('galactic credits'))

    def test_terms_exist_in_english_and_polish(self):
        for term in ('inventory item', 'inventory item instructions', 'item actions', 'sell for', 'sell one for',
                     'sell all for', 'choose how many to sell', 'cannot be sold', 'sell all instructions',
                     'yes sell all', 'no keep them', 'nothing sold', 'sold for', 'sale failed',
                     'item no longer in inventory', 'sell window instructions'):
            entry = lang._TRANSLATIONS[term]
            self.assertEqual(set(entry), {'en', 'pl'}, term)
            self.assertEqual(entry['en'].count('{}'), entry['pl'].count('{}'), term)


if __name__ == '__main__':
    unittest.main()
