"""Build placement from the lot grid: the product bridge, the client's drop
acknowledgement, fail-closed checks, payment, undo, sell and rotation.
Fake game modules only. Run with py -3.7 tools/test_placement.py.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env     # shared stubs: sims4.commands, settings, speech

speech = env.speech


class Vec(object):
    def __init__(self, x, y=0.0, z=0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)


class Definition(object):
    def __init__(self, def_id, price, flags=0, name='def'):
        self.id, self.price, self.flags, self.name = def_id, price, flags, name


class Funds(object):
    def __init__(self, money):
        self.money = money
        self.fail_remove = None     # None, 'refuse', 'raise', 'partial'
        self.fail_add = None        # None, 'raise', 'partial'
        self.calls = []

    def try_remove(self, amount, reason, sim=None):
        self.calls.append(('remove', amount, reason))
        if self.fail_remove == 'raise':
            raise RuntimeError('funds broke')
        if self.fail_remove == 'partial':
            self.money -= amount // 2
            raise RuntimeError('half way')
        if self.fail_remove == 'refuse' or amount > self.money:
            return False
        self.money -= amount
        return True

    def add(self, amount, reason, sim=None, count_as_earnings=True):
        self.calls.append(('add', amount, reason, count_as_earnings))
        if self.fail_add == 'raise':
            raise RuntimeError('cannot add')
        if self.fail_add == 'partial':
            self.money += amount // 2
            raise RuntimeError('half way')
        self.money += amount


class FakeInventory(object):
    def __init__(self, items, shared):
        self.items, self.is_shared_inventory = items, shared

    def __iter__(self):
        if self.items is None:
            raise RuntimeError('storage gone')
        return iter(self.items)


class Slot(object):
    def __init__(self, deco=False, empty=True, valid=True):
        self._deco, self.empty, self._valid = deco, empty, valid

    def is_deco_slot(self):
        return self._deco

    def is_valid_for_placement(self, obj=None):
        return self._valid

    def add_child(self, obj):
        obj.parent = self


class Obj(object):
    def __init__(self, obj_id, definition, position=None, slots=()):
        self.id, self.definition = obj_id, definition
        self.position = position or Vec(0, 0, 0)
        self.orientation = 0.0
        self.routing_surface = 'surface'
        self.level = 0
        self.parent = None
        self.slots = list(slots)
        self.destroyed = False
        self.moves = []
        self.current_value = definition.price
        self.owner = None
        self.hidden = False
        self.in_inventory = False
        self.non_deletable = False
        self.non_deletable_by_user = False
        self.is_sim = False

    def set_household_owner_id(self, owner):
        if world.owner_raise:
            raise RuntimeError('owner broke')
        self.owner = owner

    def get_household_owner_id(self):
        return self.owner

    def is_hidden(self):
        return self.hidden

    def move_to(self, **kwargs):
        self.moves.append(kwargs)
        if 'translation' in kwargs:
            self.position = kwargs['translation']
        if 'orientation' in kwargs:
            self.orientation = kwargs['orientation']

    def destroy(self, source=None, cause=None):
        if world.fail_destroy:
            raise RuntimeError('cannot destroy')
        self.destroyed = True
        world.objects.pop(self.id, None)

    def is_in_inventory(self):
        return self.in_inventory

    def get_runtime_slots_gen(self):
        return iter(self.slots)


world = types.SimpleNamespace()


def reset_world():
    world.zone_id = 7
    world.household = 41
    world.build = True
    world.funds = Funds(1000)
    world.definitions = {501: Definition(501, 300), 502: Definition(502, 40, flags=1024),
                         503: Definition(503, 90, flags=2), 504: Definition(504, 0)}
    world.objects = {}
    world.next_id = 9000
    world.on_lot = True
    world.pool = False
    world.flags_raise = False
    world.fgl = 'ok'
    world.fgl_calls = []
    world.register_ok = True
    world.registered = []
    world.fail_destroy = False
    world.ui = []
    world.lot_raise = False
    world.owner_raise = False


services = types.ModuleType('services')
services.current_zone_id = lambda: world.zone_id
services.current_zone = lambda: types.SimpleNamespace(is_in_build_buy=world.build, id=world.zone_id)
services.active_household = lambda: types.SimpleNamespace(funds=world.funds, id=world.household)


class _DefManager(object):
    def get(self, def_id, get_fallback_definition_id=True):
        if get_fallback_definition_id:
            raise AssertionError('fallback definitions must never be requested')
        return world.definitions.get(def_id)


services.definition_manager = lambda: _DefManager()


class _Lot(object):
    def is_position_on_lot(self, position):
        if world.lot_raise:
            raise RuntimeError('lot broke')
        return world.on_lot


services.active_lot = lambda: _Lot()
services.object_manager = lambda: types.SimpleNamespace(
    get=lambda obj_id: world.objects.get(obj_id), values=lambda: list(world.objects.values()))

build_buy = types.ModuleType('build_buy')


def _flags(def_id):
    if world.flags_raise:
        raise RuntimeError('no flags')
    return world.definitions[def_id].flags


build_buy.get_object_placement_flags = _flags
build_buy.is_location_pool = lambda position, level: world.pool


def _register(obj_id):
    if not isinstance(obj_id, int):
        raise TypeError('argument 1 must be int')
    if not world.register_ok:
        raise RuntimeError('not accepted')
    world.registered.append(obj_id)


build_buy.add_object_to_buildbuy_system = _register

placement = types.ModuleType('placement')
placement.create_starting_location = lambda position=None, orientation=None, routing_surface=None: (position, orientation)


def _context(start, obj, test_buildbuy_allowed=True, max_distance=None, ignored_object_ids=None):
    world.fgl_calls.append({'tests': test_buildbuy_allowed, 'max': max_distance,
                            'ignore': ignored_object_ids, 'start': start})
    return start


def _fgl(context):
    if world.fgl == 'none':
        return (None, None, 'FGL Failed')
    position, orientation = context
    return (Vec(position.x + 1, 0, position.z), orientation, 'FGL Successful')


placement.create_fgl_context_for_object = _context
placement.find_good_location = _fgl

objects_pkg = types.ModuleType('objects')
objects_system = types.ModuleType('objects.system')


def _create(def_id):
    world.next_id += 1
    obj = Obj(world.next_id, world.definitions[def_id])
    world.objects[obj.id] = obj
    return obj


objects_system.create_object = _create
objects_pkg.system = objects_system

math_stub = types.ModuleType('sims4.math')
math_stub.PI = 3.0
math_stub.angle_to_yaw_quaternion = lambda angle: ('yaw', round(angle, 3))
math_stub.yaw_quaternion_to_angle = lambda q: q[1] if isinstance(q, tuple) else float(q)
env.sims4.math = math_stub

distributor = types.ModuleType('distributor')
distributor.ops = types.SimpleNamespace(SendUIMessage=lambda name: name)
distributor.system = types.SimpleNamespace(Distributor=types.SimpleNamespace(
    instance=lambda: types.SimpleNamespace(add_op_with_no_owner=world.ui.append if False else (lambda op: world.ui.append(op)))))

consts = types.ModuleType('protocolbuffers.Consts_pb2')
consts.FUNDS_OBJECT_BUY = 11
consts.FUNDS_OBJECT_SELL = 12
consts.FUNDS_MONEY_CHEAT = 1
protocolbuffers = types.ModuleType('protocolbuffers')
protocolbuffers.Consts_pb2 = consts

reset_world()
sys.modules.update({'services': services, 'build_buy': build_buy, 'placement': placement,
                    'objects': objects_pkg, 'objects.system': objects_system,
                    'sims4.math': math_stub, 'distributor': distributor,
                    'distributor.ops': distributor.ops, 'distributor.system': distributor.system,
                    'protocolbuffers': protocolbuffers, 'protocolbuffers.Consts_pb2': consts})

import tyjokr_a11y_place as place   # noqa: E402


class Timer(object):
    made = []

    def __init__(self, seconds, callback):
        self.seconds, self.callback = seconds, callback
        Timer.made.append(self)

    def start(self):
        pass


class PlacementTests(unittest.TestCase):
    def setUp(self):
        reset_world()
        self.spoken = []
        self.parts = []
        Timer.made = []
        env.queue.clear()
        place._product = None
        del place._history[:]
        place._last.update(obj_id=None, position=None)
        place._repeat[:] = [(), 0.0]
        place._sell[:] = [None, 0.0]
        place._pending.update(serial=0, at=0.0, args=None, zone=None, product=None)
        place._owed = {}
        self.followed = []
        self.clock = [100.0]
        for item in (patch.object(place, '_say_text', lambda en, pl: self.spoken.append(en)),
                     patch.object(place, '_say', lambda parts: self.parts.append(''.join(
                         p if isinstance(p, str) else '<loc>' for p in parts))),
                     patch.object(place, '_where', lambda obj, position, level: '1 meters east'),
                     patch.object(place, '_name_parts', lambda obj: 'Desk'),
                     patch.object(place, '_follow', lambda obj, level: self.followed.append((obj.id, level)) or True),
                     patch.object(place.time, 'monotonic', lambda: self.clock[0]),
                     patch('threading.Timer', Timer)):
            item.start()
            self.addCleanup(item.stop)

    # helpers
    def choose(self, def_id=501, name='Bed'):
        self.assertTrue(place.set_product(str(def_id), name))

    def request(self, x=3, z=4):
        return place.place(Vec(x, 0, z), 0, 'surface')

    def serial(self):
        return place._pending['serial']

    def ack(self, state='ok', serial=None):
        return place.buildhand('{}|{}'.format(self.serial() if serial is None else serial, state))

    def said(self, text):
        return any(text in line for line in self.spoken + self.parts)

    # ---- product bridge
    def test_product_bridge(self):
        self.assertTrue(place.buildproduct('501|B%C5%82%C4%99kitne%20%C5%82%C3%B3%C5%BCko'))
        self.assertEqual(place.product()['name'], 'Błękitne łóżko')
        self.assertTrue(place.buildproduct('0|'))
        self.assertIsNone(place.product())
        self.assertFalse(place.buildproduct('777|Unknown'))          # not a definition
        self.assertIsNone(place.product())
        self.assertFalse(place.buildproduct('501'))                   # no separator
        asked = []
        with patch.object(world, 'definitions', dict(world.definitions)):
            world.definitions[18446744073709551615] = Definition(18446744073709551615, 5)
            self.assertTrue(place.buildproduct('18446744073709551615|Huge'))   # full 64 bits, no rounding
            self.assertEqual(place.product()['id'], 18446744073709551615)
        self.assertFalse(place.buildproduct('18446744073709551614|Near'))      # one off: not that object
        self.assertIsNone(place.product())
        self.choose()
        world.zone_id = 8
        self.assertIsNone(place.product())                            # another lot forgets it

    # ---- refusals before anything exists
    def test_refusals_create_nothing(self):
        self.assertFalse(self.request())
        self.assertTrue(self.said('Choose an object'))
        self.choose()
        world.build = False
        self.assertFalse(self.request())
        self.assertTrue(self.said('Enter Build mode'))
        world.build = True
        world.funds.money = 10
        self.assertFalse(self.request())
        self.assertTrue(self.said('Not enough money'))
        world.funds.money = 1000
        world.on_lot = False
        self.assertFalse(self.request())
        world.on_lot, world.pool = True, True
        self.assertFalse(self.request())
        world.pool, world.lot_raise = False, True
        self.assertFalse(self.request())
        self.assertTrue(self.said('could not be checked'))
        world.lot_raise, world.flags_raise = False, True
        self.assertFalse(self.request())
        self.assertTrue(self.said('did not say where'))
        world.flags_raise = False
        self.choose(503, 'Painting')
        self.assertFalse(self.request())
        self.assertTrue(self.said('hangs on a wall'))
        self.assertEqual(world.objects, {})
        self.assertEqual(world.ui, [])
        self.assertEqual(world.funds.money, 1000)

    # ---- the client acknowledgement
    def test_nothing_is_created_before_the_client_answers(self):
        self.choose()
        self.assertTrue(self.request())
        self.assertEqual(world.ui, ['A11y|buildhand|drop|1'])
        self.assertEqual(world.objects, {})
        self.assertEqual(Timer.made[0].seconds, place.ACK_SECONDS)
        self.assertFalse(self.request())
        self.assertTrue(self.said('Still placing'))
        self.assertTrue(self.ack('ok'))
        self.assertEqual(len(world.objects), 1)

    def test_denied_wrong_serial_and_timeout_create_nothing(self):
        self.choose()
        self.request()
        self.assertFalse(self.ack('denied'))
        self.assertTrue(self.said('Press Escape to put down the current Build tool'))
        self.assertFalse(self.ack('ok'))                              # already answered
        self.clock[0] += 5
        self.request()
        self.assertFalse(self.ack('ok', serial=self.serial() - 1))    # stale serial
        Timer.made[-1].callback()
        env.drain()
        self.assertTrue(self.said('did not answer'))
        self.assertFalse(self.ack('ok'))                              # too late
        self.assertFalse(place.buildhand('1|held'))
        self.assertEqual(world.objects, {})
        self.assertEqual(world.funds.money, 1000)

    def test_changes_while_waiting_drop_the_placement(self):
        for change in ('zone', 'build', 'product', 'grid'):
            reset_world()
            self.choose()
            self.clock[0] += 10
            self.request()
            if change == 'zone':
                world.zone_id = 99
            elif change == 'build':
                world.build = False
            elif change == 'product':
                self.choose(504, 'Rug')
            else:
                place.cancel_pending()
            self.assertFalse(self.ack('ok'), change)
            self.assertEqual(world.objects, {}, change)

    # ---- placing
    def test_placement_uses_the_checked_search_only(self):
        self.choose()
        self.request()
        self.assertTrue(self.ack('ok'))
        obj = list(world.objects.values())[0]
        self.assertEqual([c['tests'] for c in world.fgl_calls], [True])
        self.assertEqual(world.fgl_calls[0]['max'], place.SEARCH_RADIUS)
        self.assertEqual(world.registered, [obj.id])
        self.assertEqual(world.funds.money, 700)
        self.assertEqual(world.funds.calls[0], ('remove', 300, 11))
        self.assertTrue(self.said('Bed placed, 1 meters east from the cursor, 300 simoleons.'))

    def test_no_room_means_no_object_and_no_charge(self):
        self.choose()
        world.fgl = 'none'
        self.request()
        self.assertFalse(self.ack('ok'))
        self.assertTrue(self.said('No room'))
        self.assertEqual(len(world.fgl_calls), 1)                     # no untested retry
        self.assertEqual(world.objects, {})
        self.assertEqual(world.funds.money, 1000)

    def test_registration_failure_undoes_everything(self):
        self.choose()
        world.register_ok = False
        self.request()
        self.assertFalse(self.ack('ok'))
        self.assertTrue(self.said('would not accept'))
        self.assertEqual(world.objects, {})
        self.assertEqual(world.funds.money, 1000)

    def test_payment_failures(self):
        self.choose()
        world.funds.fail_remove = 'raise'
        self.request()
        self.assertFalse(self.ack('ok'))
        self.assertEqual((world.objects, world.funds.money), ({}, 1000))
        self.clock[0] += 10
        world.funds.fail_remove = 'partial'
        self.request()
        self.assertFalse(self.ack('ok'))
        self.assertEqual(world.objects, {})
        self.assertEqual(world.funds.money, 1000)                     # the half taken came back
        self.assertEqual(world.funds.calls[-1][:3], ('add', 150, 12))

    def test_surface_objects_need_a_valid_free_slot(self):
        desk = Obj(1, Definition(1, 0, name='desk_modern'), Vec(3, 0, 4),
                   slots=[Slot(deco=True), Slot(empty=False), Slot(valid=False), Slot()])
        world.objects[1] = desk
        self.choose(502, 'Laptop')
        self.request()
        self.assertTrue(self.ack('ok'))
        laptop = [o for o in world.objects.values() if o.id != 1][0]
        self.assertIs(laptop.parent, desk.slots[3])
        self.assertTrue(self.said('Laptop placed on Desk'))
        desk.slots = [Slot(deco=True)]
        self.clock[0] += 10
        self.request(x=5)
        self.assertFalse(self.ack('ok'))
        self.assertTrue(self.said('free spot on a desk'))
        self.assertEqual(world.funds.money, 960)

    def test_repeat_on_the_same_tile_needs_a_second_press(self):
        self.choose()
        self.request()
        self.ack('ok')
        self.clock[0] += 1
        self.assertFalse(self.request())
        self.assertTrue(self.said('Already placed here'))
        self.assertTrue(self.request())                               # the second press is meant
        self.ack('ok')
        self.assertEqual(len(world.objects), 2)
        self.clock[0] += 1
        self.assertTrue(self.request(x=8))                            # another tile: no question
        self.ack('ok')
        self.assertEqual(len(world.objects), 3)

    # ---- undo, sell, debts
    def test_undo_refunds_once_and_skips_objects_removed_elsewhere(self):
        self.choose()
        self.request(x=1)
        self.ack('ok')
        self.clock[0] += 5
        self.request(x=2)
        self.ack('ok')
        first, second = sorted(world.objects)
        world.objects.pop(second)                                     # sold natively meanwhile
        self.assertTrue(place.undo())
        self.assertNotIn(first, world.objects)
        self.assertEqual(world.funds.money, 1000 - 600 + 300)         # only the first refunded
        self.assertEqual(world.funds.calls[-1], ('add', 300, 12, False))
        self.assertFalse(place.undo())
        self.assertTrue(self.said('Nothing to undo'))

    def test_failed_refund_becomes_a_debt_paid_next_time(self):
        self.choose()
        self.request()
        self.ack('ok')
        world.funds.fail_add = 'raise'
        self.assertTrue(place.undo())
        self.assertEqual(place.owed(), 300)
        self.assertTrue(self.said('will be retried'))
        world.funds.fail_add = None
        place.sell(None)                                              # any Build money action settles first
        self.assertEqual(place.owed(), 0)
        self.assertEqual(world.funds.money, 1000)
        world.funds.fail_add = 'partial'
        self.assertTrue(place._refund(100) is False)
        self.assertEqual(place.owed(), 50)

    def test_undo_keeps_history_when_removal_fails(self):
        self.choose()
        self.request()
        self.ack('ok')
        world.fail_destroy = True
        self.assertFalse(place.undo())
        self.assertEqual(len(place._history), 1)
        self.assertEqual(world.funds.money, 700)

    def test_sell_needs_two_presses(self):
        chair = Obj(5, Definition(5, 120))
        world.objects[5] = chair
        self.assertFalse(place.sell(chair))
        self.assertIn(5, world.objects)
        self.clock[0] += place.SELL_CONFIRM_SECONDS + 1
        self.assertFalse(place.sell(chair))                           # too slow: asks again
        self.assertTrue(place.sell(chair))
        self.assertNotIn(5, world.objects)
        self.assertEqual(world.funds.money, 1120)

    # ---- rotation
    def test_rotation_turns_the_last_object_where_it_fits(self):
        self.assertFalse(place.rotate(1))
        self.choose()
        self.request()
        self.ack('ok')
        obj = world.objects[place._last['obj_id']]
        self.assertTrue(place.rotate(1))
        self.assertEqual(obj.orientation, ('yaw', 1.5))
        self.assertEqual(world.fgl_calls[-1]['ignore'], [obj.id])
        world.fgl = 'none'
        self.assertFalse(place.rotate(-1))
        self.assertEqual(obj.orientation, ('yaw', 1.5))
        obj.parent = object()
        self.assertFalse(place.rotate(1))
        self.assertTrue(self.said('keeps its direction'))

    def test_a_late_answer_is_refused_even_before_the_timer_runs(self):
        self.choose()
        self.request()
        self.clock[0] += place.ACK_SECONDS + 0.1
        self.assertFalse(self.ack('ok'))
        self.assertTrue(self.said('did not answer'))
        Timer.made[-1].callback()
        env.drain()
        self.assertEqual(sum('did not answer' in line for line in self.spoken), 1)   # said once
        self.assertEqual(world.objects, {})

    def test_the_cursor_follows_the_placed_object(self):
        self.choose()
        self.request()
        self.ack('ok')
        obj_id = place._last['obj_id']
        self.assertEqual(self.followed, [(obj_id, 0)])
        self.assertTrue(self.said('The cursor moved to it.'))

    def test_undo_and_debts_belong_to_one_household_and_lot(self):
        self.choose()
        self.request()
        self.ack('ok')
        world.household = 42                                          # another family is active
        self.assertFalse(place.undo())
        self.assertEqual(len(world.objects), 1)
        world.household, world.zone_id = 41, 8                        # same family, another lot
        self.assertFalse(place.undo())
        world.zone_id = 7
        world.funds.fail_add = 'raise'
        self.assertTrue(place.undo())
        self.assertEqual(place.owed(), 300)
        world.household = 42
        world.funds.fail_add = None
        self.assertEqual(place.owed(), 0)
        place.sell(None)                                              # settles 42's debt: none
        self.assertEqual(place._owed, {41: 300})
        world.household = 41
        place.sell(None)
        self.assertEqual(place._owed, {})

    def test_placed_objects_belong_to_the_household(self):
        self.choose()
        self.request()
        self.ack('ok')
        self.assertEqual(world.objects[place._last['obj_id']].owner, 41)

    def test_any_exception_after_creation_removes_the_object(self):
        self.choose()
        world.owner_raise = True
        self.request()
        self.assertFalse(self.ack('ok'))
        self.assertTrue(self.said('could not place that object'))
        self.assertEqual(world.objects, {})
        self.assertEqual(world.funds.money, 1000)

    def test_an_occupied_object_is_never_sold_or_undone(self):
        # Live 2026-09-26: X offered a desk with a computer in its slot, for
        # the desk's value only; confirming would have taken the computer.
        desk = Obj(70, Definition(70, 1000))
        laptop = Obj(71, Definition(71, 640))
        desk.children, world.objects[70], world.objects[71] = [laptop], desk, laptop
        self.assertFalse(place.sell(desk))
        self.assertFalse(place.sell(desk))                            # never confirmable
        self.assertTrue(self.said('Something is on it, inside it or using it'))
        self.assertIn(70, world.objects)
        place.sell(laptop)
        self.assertTrue(place.sell(laptop))
        desk.children = []
        place.sell(desk)
        self.assertTrue(place.sell(desk))
        self.assertEqual(world.funds.money, 1000 + 640 + 1000)
        # Any child blocks, hidden ones included (they may carry value).
        chair = Obj(72, Definition(72, 100))
        ghost = Obj(73, Definition(73, 0))
        ghost.hidden = True
        chair.children, world.objects[72] = [ghost], chair
        self.assertFalse(place.sell(chair))
        self.assertFalse(place.sell(chair))
        self.assertIn(72, world.objects)

    def test_an_object_holding_items_is_never_sold(self):
        # EA purges an unshared inventory with its owner; a shared one
        # (such as the fridges') survives, so it does not block.
        chest = Obj(74, Definition(74, 300))
        world.objects[74] = chest
        chest.inventory_component = FakeInventory(['book'], shared=False)
        self.assertFalse(place.sell(chest))
        self.assertFalse(place.sell(chest))
        self.assertTrue(self.said('inside it'))
        self.assertIn(74, world.objects)
        chest.inventory_component = FakeInventory(['plate'], shared=True)
        place.sell(chest)
        self.assertTrue(place.sell(chest))
        broken = Obj(75, Definition(75, 300))
        broken.inventory_component = FakeInventory(None, shared=False)   # iteration raises
        world.objects[75] = broken
        self.assertFalse(place.sell(broken))
        self.assertFalse(place.sell(broken))
        self.assertIn(75, world.objects)

    def test_undo_refuses_an_occupied_placement(self):
        self.choose()
        self.request()
        self.ack('ok')
        obj = world.objects[place._last['obj_id']]
        paid = world.funds.money
        obj.children = [Obj(80, Definition(80, 50))]
        self.assertFalse(place.undo())
        self.assertTrue(self.said('Remove that first'))
        self.assertIn(obj.id, world.objects)
        self.assertEqual(world.funds.money, paid)
        self.assertEqual(len(place._history), 1)
        obj.children = []
        self.assertTrue(place.undo())
        self.assertNotIn(obj.id, world.objects)

    def test_sell_refuses_what_the_household_may_not_sell(self):
        def item(**kw):
            obj = Obj(60 + len(world.objects), Definition(60, 50))
            obj.owner = 41
            for key, value in kw.items():
                setattr(obj, key, value)
            world.objects[obj.id] = obj
            return obj
        cases = [(item(is_sim=True), 'Sims cannot be sold'),
                 (item(hidden=True), 'cannot be sold from here'),
                 (item(in_inventory=True), 'cannot be sold from here'),
                 (item(non_deletable=True), 'does not allow deleting'),
                 (item(non_deletable_by_user=True), 'does not allow deleting'),
                 (item(owner=99), 'another household')]
        for obj, text in cases:
            self.assertFalse(place.sell(obj))
            self.assertFalse(place.sell(obj))                         # never confirmable
            self.assertTrue(self.said(text), text)
            self.assertIn(obj.id, world.objects)
        world.on_lot = False
        self.assertFalse(place.sell(item()))
        self.assertTrue(self.said('not on this lot'))
        world.on_lot = True
        unowned = item(owner=None)                                    # lot objects without an owner
        place.sell(unowned)
        self.assertTrue(place.sell(unowned))
        self.assertEqual(world.funds.money, 1050)

    def test_rotation_belongs_to_the_household_and_lot(self):
        self.choose()
        self.request()
        self.ack('ok')
        world.household = 42
        self.assertFalse(place.rotate(1))
        self.assertTrue(self.said('Place an object first'))
        world.household, world.zone_id = 41, 8
        self.assertFalse(place.rotate(1))
        world.zone_id = 7
        self.assertTrue(place.rotate(1))

    def test_rotate_undo_and_sell_need_build_mode(self):
        self.choose()
        self.request()
        self.ack('ok')
        obj_id = place._last['obj_id']
        chair = Obj(70, Definition(70, 80))
        world.objects[70] = chair
        world.build = False                                           # the Live-mode grid
        for action in (lambda: place.rotate(1), place.undo, lambda: place.sell(chair), lambda: place.sell(chair)):
            self.assertFalse(action())
        self.assertEqual(sum('Enter Build mode first' in line for line in self.spoken), 4)
        self.assertIn(obj_id, world.objects)
        self.assertIn(70, world.objects)
        self.assertEqual(world.funds.money, 700)
        world.build = True
        self.assertTrue(place.undo())

    def test_the_landed_tile_is_guarded_too(self):
        self.choose()
        self.request(x=3)                                             # the fake search lands one tile east
        self.ack('ok')
        self.clock[0] += 1
        self.assertFalse(self.request(x=4))                           # Enter again where the cursor followed
        self.assertTrue(self.said('Already placed here'))
        self.assertEqual(len(world.objects), 1)

    def test_nothing_after_payment_can_remove_a_paid_object(self):
        self.choose()
        with patch.object(place, '_follow', side_effect=RuntimeError('grid broke')):
            self.request()
            self.assertTrue(self.ack('ok'))
        self.assertEqual(len(world.objects), 1)
        self.assertEqual(world.funds.money, 700)
        self.assertEqual(len(place._history), 1)
        self.assertTrue(self.said('Placed.'))
        self.assertTrue(place.undo())                                 # and it can still be undone
        self.assertEqual(world.funds.money, 1000)

    def test_a_worthless_object_sells_for_nothing(self):
        broken = Obj(80, Definition(80, 500))
        broken.current_value = 0
        world.objects[80] = broken
        place.sell(broken)
        self.assertTrue(place.sell(broken))
        self.assertEqual(world.funds.money, 1000)                     # not the 500 catalog price
        unknown = Obj(81, Definition(81, 90))
        unknown.current_value = None
        world.objects[81] = unknown
        place.sell(unknown)
        self.assertTrue(place.sell(unknown))
        self.assertEqual(world.funds.money, 1090)                     # no value known: catalog price

    def test_speech_and_its_fallback_failing_after_payment_keep_the_object(self):
        self.choose()
        with patch.object(place, '_say', side_effect=RuntimeError('speech gone')),                 patch.object(place, '_say_text', side_effect=RuntimeError('fallback gone')):
            self.request()
            self.assertTrue(self.ack('ok'))
        self.assertEqual(len(world.objects), 1)
        self.assertEqual(world.funds.money, 700)
        self.assertEqual(len(place._history), 1)

    def test_bookkeeping_failing_after_payment_keeps_the_object(self):
        class Broken(list):
            def append(self, item):
                raise RuntimeError('history broke')
        self.choose()
        with patch.object(place, '_history', Broken()):
            self.request()
            self.assertTrue(self.ack('ok'))
        self.assertEqual(len(world.objects), 1)
        self.assertEqual(world.funds.money, 700)

    def test_landing_at_the_cursor_is_worded_plainly(self):
        self.choose()
        with patch.object(place, '_where', lambda obj, position, level: place.lang.t('here')):
            self.request()
            self.ack('ok')
        self.assertTrue(self.said('Bed placed at the cursor, 300 simoleons.'))
        self.assertFalse(self.said('here from the cursor'))

    def test_surfaces_must_be_visible_on_the_lot_and_ours(self):
        for label, change in (('hidden', {'hidden': True}), ('foreign', {'owner': 99}), ('offlot', {})):
            reset_world()
            desk = Obj(1, Definition(1, 0, name='desk_modern'), Vec(3, 0, 4), slots=[Slot()])
            for key, value in change.items():
                setattr(desk, key, value)
            world.objects[1] = desk
            if label == 'offlot':
                calls = []
                world.on_lot = True
                original = _Lot.is_position_on_lot
                def on_lot(lot_self, position, desk=desk):
                    return position is not desk.position
                with patch.object(_Lot, 'is_position_on_lot', on_lot):
                    self.choose(502, 'Laptop')
                    self.clock[0] += 10
                    self.request()
                    self.assertFalse(self.ack('ok'), label)
            else:
                self.choose(502, 'Laptop')
                self.clock[0] += 10
                self.request()
                self.assertFalse(self.ack('ok'), label)
            self.assertIsNone(desk.slots[0].__dict__.get('child'), label)
            self.assertEqual(world.funds.money, 1000, label)

    def test_build_exit_forgets_the_product_and_pending(self):
        self.choose()
        self.request()
        place.forget()
        self.assertIsNone(place.product())
        self.assertFalse(self.ack('ok'))
        self.assertEqual(world.objects, {})

    def test_source_has_no_dashes(self):
        with open(place.__file__, encoding='utf-8') as handle:
            text = handle.read()
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)


if __name__ == '__main__':
    unittest.main()
