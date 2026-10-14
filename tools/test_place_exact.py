"""Exact placement for the Build cursor: after the client puts down EA's held
product, the object goes exactly to the requested point and facing (no
nearby search) once the game's own placement test accepts the real object;
if it no longer fits, the object is removed and nothing is charged. Uses the
placement tests' fake game.
"""
import unittest
from unittest.mock import patch

import test_placement as base
import tyjokr_a11y_tiles as tiles

place = base.place
world = base.world
Vec = base.Vec


class ExactTests(base.PlacementTests):
    def exact(self, fits=(True, None), angle=1.5):
        self.choose()
        with patch.object(tiles, 'test_fit', return_value=fits) as test_fit, \
                patch.object(tiles, 'frame', return_value=None):
            self.assertTrue(place.place(Vec(3.5, 0, 4.5), 0, 'surface', angle=angle, exact=True))
            result = self.ack('ok')
        return result, test_fit

    def test_exact_places_at_the_point_and_facing_without_searching(self):
        result, test_fit = self.exact()
        self.assertTrue(result)
        obj = list(world.objects.values())[0]
        self.assertEqual(world.fgl_calls, [])
        self.assertEqual(obj.moves[-1]['translation'].x, 3.5)
        self.assertEqual(obj.moves[-1]['orientation'], ('yaw', 1.5))
        test_fit.assert_called_once()
        self.assertIs(test_fit.call_args[0][0], obj)              # tested with the real object
        self.assertEqual(world.funds.money, 700)
        self.assertTrue(self.said('Bed placed, 300 simoleons.'))

    def test_exact_refuses_when_the_real_object_no_longer_fits(self):
        result, _test_fit = self.exact(fits=(False, 'a wall is in the way'))
        self.assertFalse(result)
        self.assertEqual(world.objects, {})
        self.assertEqual(world.funds.money, 1000)
        self.assertTrue(self.said('It no longer fits there (a wall is in the way), so nothing was bought.'))

    def test_an_unanswered_final_test_still_places(self):
        result, _test_fit = self.exact(fits=(None, None))       # the cursor's own test already passed
        self.assertTrue(result)
        self.assertEqual(len(world.objects), 1)


if __name__ == '__main__':
    suite = unittest.TestSuite(ExactTests(name) for name in unittest.TestLoader().getTestCaseNames(ExactTests)
                               if name.startswith('test_exact') or name.startswith('test_an_unanswered'))
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
