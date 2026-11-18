"""Integrated surface targeting keeps native slot validation and payment."""
import unittest
from unittest.mock import patch
import test_placement as env
import tyjokr_a11y_layers as layers

class FocusedSurfaceTests(unittest.TestCase):
    setUp_base = env.PlacementTests.setUp
    choose = env.PlacementTests.choose
    ack = env.PlacementTests.ack
    serial = env.PlacementTests.serial
    said = env.PlacementTests.said
    def setUp(self):
        self.setUp_base()
        self.slot=env.Slot(deco=True)
        self.target=env.Obj(77,env.Definition(700,100),slots=[self.slot])
        self.target.owner=env.world.household
        env.world.objects[77]=self.target
        self.focus=patch.object(layers,'focused_target',lambda:self.target)
        self.focus.start();self.addCleanup(self.focus.stop)
        self.choose()
    def request(self):
        return env.place.place(env.Vec(3,0,4),0,'surface',surface_id=77)
    def test_validated_decoration_slot_uses_normal_transaction(self):
        self.assertTrue(self.request());self.assertTrue(self.ack())
        self.assertEqual(env.world.funds.money,700)
        placed=env.world.objects[env.place._last['obj_id']]
        self.assertIs(placed.parent,self.slot)
        self.assertEqual(placed.moves,[])
        self.assertEqual(env.world.fgl_calls,[])
    def test_full_surface_never_falls_back_to_floor(self):
        self.slot.empty=False
        self.assertTrue(self.request());self.assertFalse(self.ack())
        self.assertEqual(env.world.funds.money,1000)
        self.assertEqual(set(env.world.objects),{77})
        self.assertTrue(self.said('Nothing was bought'))
    def test_incompatible_slot_never_uses_a_nearby_surface(self):
        self.slot._valid=False
        self.assertTrue(self.request());self.assertFalse(self.ack())
        self.assertEqual(env.world.funds.money,1000)
    def test_focus_change_before_acknowledgement_refuses(self):
        self.assertTrue(self.request());self.target=None
        self.assertFalse(self.ack());self.assertEqual(env.world.funds.money,1000)
    def test_other_household_surface_refused(self):
        self.target.owner=999
        self.assertTrue(self.request());self.assertFalse(self.ack())
        self.assertEqual(env.world.funds.money,1000)
    def test_busy_request_does_not_replace_the_selected_surface(self):
        self.assertTrue(self.request());serial=self.serial()
        self.assertFalse(env.place.place(env.Vec(9,0,9),0,'surface',surface_id=88))
        self.assertEqual(env.place._pending['surface_id'],77)
        self.assertEqual(self.serial(),serial)
        self.assertTrue(self.ack())
    def test_attached_children_are_reachable_once_even_with_cycles(self):
        child=env.Obj(78,env.Definition(701,1))
        import tyjokr_a11y_tiles as tiles
        with patch.object(tiles,'children_on',side_effect=lambda o:[child] if o is self.target else [self.target]):
            self.assertEqual(layers._focus_objects([self.target,child]),[self.target,child])

if __name__=='__main__':unittest.main()
