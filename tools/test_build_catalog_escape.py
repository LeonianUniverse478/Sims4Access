"""a11y.catalogleft: after Escape releases the Build catalog, the player hears
that they left it, which object stays chosen, and how to place it or return.
The chosen product is not changed. Uses the placement tests' fake game.
"""
import unittest
from unittest.mock import patch

import test_placement as base

place = base.place


class CatalogLeftTests(unittest.TestCase):
    def setUp(self):
        self.spoken = []
        speaker = patch.object(base.speech, 'speak', side_effect=lambda text, *a, **k: self.spoken.append(text))
        speaker.start()
        self.addCleanup(speaker.stop)
        self.addCleanup(place.forget)

    def test_names_the_chosen_object_and_keeps_it(self):
        with patch.object(place, '_product', {'id': 7, 'name': 'Cheap Bed', 'zone': place._zone_id()}):
            self.assertTrue(place.catalogleft('1'))
            self.assertEqual(place.product()['name'], 'Cheap Bed')
        self.assertEqual(len(self.spoken), 1)
        self.assertIn('Left the Build catalog', self.spoken[0])
        self.assertIn('Cheap Bed chosen', self.spoken[0])
        self.assertIn('Control Alt B', self.spoken[0])
        self.assertIn('Tab returns', self.spoken[0])

    def test_without_a_chosen_object(self):
        with patch.object(place, '_product', None):
            place.catalogleft('1')
        self.assertEqual(self.spoken, ['Left the Build catalog. Tab returns to the catalog.'])


if __name__ == '__main__':
    unittest.main()
