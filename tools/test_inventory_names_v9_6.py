"""Inventory fallback must preserve native rich/lazy tooltips and hidden items."""
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from unittest.mock import Mock, patch
import test_scanner_v5 as env


class InventoryNameTests(unittest.TestCase):
    def setUp(self):
        self.items = []
        self.base_added = Mock(return_value='native result')
        self.base_rebuild = Mock(return_value='rebuilt')
        self.item_class = type('InventoryItemComponent', (), {
            'on_added_to_inventory': self.base_added})
        self.tooltip_class = type('TooltipComponent', (), {
            'update_object_tooltip': self.base_rebuild})
        self.name = Mock(return_value='localized item name')
        modules = {
            'services': types.SimpleNamespace(
                inventory_manager=lambda: types.SimpleNamespace(values=lambda: self.items)),
            'indexed_manager': types.SimpleNamespace(CallbackTypes=types.SimpleNamespace(ON_OBJECT_ADD=1)),
            'objects': types.ModuleType('objects'),
            'objects.components': types.SimpleNamespace(types=types.SimpleNamespace(TOOLTIP_COMPONENT=1)),
            'objects.hovertip': types.SimpleNamespace(TooltipFields=types.SimpleNamespace(recipe_name=0)),
            'objects.components.inventory_item': types.SimpleNamespace(InventoryItemComponent=self.item_class),
            'objects.components.tooltip_component': types.SimpleNamespace(TooltipComponent=self.tooltip_class),
            'protocolbuffers': types.SimpleNamespace(UI_pb2=types.SimpleNamespace(
                UiObjectMetadata=types.SimpleNamespace(HOVER_TIP_CONSUMABLE_CRAFTABLE=2))),
            'sims4.localization': types.SimpleNamespace(LocalizationHelperTuning=types.SimpleNamespace(get_object_name=self.name)),
        }
        self.modules = patch.dict(sys.modules, modules)
        self.modules.start()
        self.addCleanup(self.modules.stop)
        path = Path(__file__).resolve().parents[1] / 'Scripts/tyjokr_a11y_objectnames.py'
        spec = importlib.util.spec_from_file_location('inventory_names_test_target', str(path))
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)
        self.mod._enabled = True

    def item(self, ident=1, hidden=False, style=None, component=None):
        return types.SimpleNamespace(
            id=ident, is_sim=False, definition=object(), hover_tip=style,
            inventoryitem_component=types.SimpleNamespace(
                is_hidden=hidden, is_in_inventory=lambda: True),
            get_component=lambda unused: component,
            super_affordances=lambda: iter(()),
            add_ui_metadata=Mock(), update_ui_metadata=Mock(), update_tooltip_field=Mock())

    def test_visible_inventory_only_item_gets_localized_name(self):
        item = self.item()
        self.assertFalse(self.mod.stamp(item))  # no world-facing interaction
        self.assertTrue(self.mod.stamp(item, inventory=True))
        self.assertEqual(item.hover_tip, 2)
        item.add_ui_metadata.assert_called_once_with('recipe_name', 'localized item name')
        item.update_ui_metadata.assert_called_once_with()
        self.assertFalse(self.mod.stamp(item, inventory=True))

    def test_rich_tooltip_is_never_replaced_even_on_force(self):
        item = self.item(style=3)
        self.assertFalse(self.mod.stamp(item, force=True, inventory=True))
        self.assertEqual(item.hover_tip, 3)
        self.name.assert_not_called()
        item.add_ui_metadata.assert_not_called()
        item.update_ui_metadata.assert_not_called()

    def test_component_uses_lazy_external_field_without_preempting_native_style(self):
        item = self.item(component=object())
        self.assertTrue(self.mod.stamp(item, inventory=True))
        self.assertIsNone(item.hover_tip)
        item.update_tooltip_field.assert_called_once_with(0, 'localized item name', should_update=True)
        item.add_ui_metadata.assert_not_called()
        item.update_ui_metadata.assert_not_called()
        component = self.tooltip_class()
        component.owner = item
        component._ui_metadata_handles = {'name': 1}
        self.assertEqual(component.update_object_tooltip(), 'rebuilt')
        self.assertEqual(item.hover_tip, 2)
        item.hover_tip = 6
        component.update_object_tooltip()
        self.assertEqual(item.hover_tip, 6)

    def test_hidden_or_removed_items_are_excluded(self):
        hidden = self.item(1, hidden=True)
        removed = self.item(2)
        removed.inventoryitem_component.is_in_inventory = lambda: False
        visible = self.item(3)
        self.items.extend((hidden, removed, visible))
        self.assertEqual(self.mod.stamp_inventory(), 1)
        hidden.add_ui_metadata.assert_not_called()
        removed.add_ui_metadata.assert_not_called()
        visible.add_ui_metadata.assert_called_once()

    def test_new_item_hook_preserves_native_result_and_setting(self):
        component = self.item_class()
        component.owner = self.item()
        self.mod._enabled = False
        self.assertEqual(component.on_added_to_inventory(), 'native result')
        component.owner.add_ui_metadata.assert_not_called()
        self.mod._enabled = True
        self.assertEqual(component.on_added_to_inventory(), 'native result')
        component.owner.add_ui_metadata.assert_called_once()
        self.assertEqual(self.base_added.call_count, 2)


if __name__ == '__main__':
    unittest.main(verbosity=2)
