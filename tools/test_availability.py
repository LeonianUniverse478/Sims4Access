"""Per-Sim availability for the scanner: the three pie outcomes, fail-open on
every error, a resumable per-test budget, supersedable ticks, Sim changes,
and no native menu ever built. Run with py -3.7 tools/test_availability.py.
"""
import sys
import types
import unittest
from unittest.mock import patch

import test_scanner_v5 as env    # shared stubs: sims4.commands, settings, speech

settings = env.settings
speech = env.speech

DEFAULT = object()
calls = {'tests': [], 'valid': [], 'sub': [], 'contexts': [], 'picks': [], 'real_log': []}


class Result(object):
    def __init__(self, ok, tooltip=None):
        self.ok = ok
        self.tooltip = tooltip

    def __bool__(self):
        return self.ok


PASS = Result(True)
HIDDEN = Result(False)
GREY = Result(False, tooltip=lambda *_, **__: 'needs cooking 3')


class ChoiceMenu(object):
    def __init__(self, *args, **kwargs):
        raise AssertionError('a ChoiceMenu was built')

    @staticmethod
    def is_valid_aop(aop, context, user_pick_target=None, result_override=DEFAULT, do_test=True):
        calls['valid'].append((aop.affordance.__name__, user_pick_target, result_override is not DEFAULT, do_test))
        if result_override is not DEFAULT:
            result = result_override
        elif user_pick_target is not None and user_pick_target.check_affordance_for_suppression(
                context.sim, aop, user_directed=True, check_option='PROVIDED_AFFORDANCE_ONLY'):
            result = Result(False)
        else:
            result = aop.test(context)
        if not result and not result.tooltip:
            result = Result(False)
        return result


choices = types.ModuleType('interactions.choices')
choices.ChoiceMenu = ChoiceMenu
choices._show_interaction_failure_reason = False
interactions = types.ModuleType('interactions')
interactions.choices = choices


class PickInfo(object):
    def __init__(self, **kwargs):
        calls['picks'].append(kwargs)
        self.kwargs = kwargs


pick_info = types.ModuleType('server.pick_info')
pick_info.PickInfo = PickInfo
pick_info.PickType = types.SimpleNamespace(PICK_OBJECT=2, PICK_SIM=3)
server = types.ModuleType('server')
server.pick_info = pick_info


class RealLogger(object):
    def exception(self, message, *args, **kwargs):
        calls['real_log'].append(message)

    def warn(self, message, *args, **kwargs):
        calls['real_log'].append('warn ' + message)


script_object = types.ModuleType('objects.script_object')
script_object.logger = RealLogger()
objects_pkg = types.ModuleType('objects')
objects_pkg.script_object = script_object

world = types.SimpleNamespace(sim=None, client=None, objects={}, lot_id=77, fire=None)
services = types.ModuleType('services')
services.get_active_sim = lambda: world.sim
services.client_manager = lambda: types.SimpleNamespace(get_first_client=lambda: world.client)
services.object_manager = lambda: types.SimpleNamespace(get=lambda obj_id: world.objects.get(obj_id))
services.active_lot = lambda: types.SimpleNamespace(lot_id=world.lot_id)
services.get_fire_service = lambda: world.fire

sys.modules.update({'services': services, 'interactions': interactions,
                    'interactions.choices': choices, 'server': server,
                    'server.pick_info': pick_info, 'objects': objects_pkg,
                    'objects.script_object': script_object})

import tyjokr_a11y_availability as availability   # noqa: E402


class Clock(object):
    def __init__(self):
        self.mono = 1000.0
        self.perf = 0.0
        self.test_cost = 0.0

    def monotonic(self):
        return self.mono

    def perf_counter(self):
        return self.perf


clock = Clock()


class Affordance(object):
    def __init__(self, name, user=True, sub=None):
        self.__name__ = name
        self.allow_user_directed = user
        self.sub = sub or []

    def potential_pie_menu_sub_interactions_gen(self, target, context, scoring_gsi_handler=None, **kwargs):
        calls['sub'].append(self.__name__)
        return iter(self.sub)


class Aop(object):
    def __init__(self, affordance, result, raises=None):
        self.affordance = affordance
        self.result = result
        self.raises = raises
        self.target = None
        self.interaction_parameters = {}

    def test(self, context):
        calls['tests'].append(self.affordance.__name__)
        clock.perf += clock.test_cost
        if self.raises is not None:
            raise self.raises
        return self.result


def row(name, result, user=True, sub=None, raises=None):
    return Aop(Affordance(name, user=user, sub=sub), result, raises=raises)


class Obj(object):
    def __init__(self, obj_id, aops=(), forwarded=(), swallow=None, suppress=()):
        self.id = obj_id
        self.aops = list(aops)
        self.forwarded_pick_targets = tuple(forwarded)
        self.swallow = swallow
        self.suppress = set(suppress)
        self.position = types.SimpleNamespace(x=float(obj_id), y=0.0, z=0.0)
        self.routing_surface = 'surface-{}'.format(obj_id)
        self.level = 1
        self.object_radius = 0.5
        self.provided_routing_surface = None
        self.provides_terrain_interactions = False
        self.provides_ocean_interactions = False
        self.definition = types.SimpleNamespace(name='def{}'.format(obj_id))
        for aop in self.aops:
            aop.target = self

    def potential_interactions(self, context, **kwargs):
        # EA's ScriptObject.potential_interactions: catches, logs through the
        # module-global logger looked up at call time, and stops yielding.
        calls['contexts'].append(context)
        try:
            for aop in self.aops:
                yield aop
            if self.swallow is not None:
                raise self.swallow
        except Exception as ex:
            sys.modules['objects.script_object'].logger.exception('Exception while generating', exc=ex)

    def check_affordance_for_suppression(self, sim, aop, user_directed=True, check_option=None):
        return aop.affordance.__name__ in self.suppress


class Context(object):
    def __init__(self, sim, pick):
        self.sim = sim
        self.pick = pick
        self.preferred_objects = set()

    def add_preferred_objects(self, objs):
        self.preferred_objects |= set(objs)


class Client(object):
    def create_interaction_context(self, sim, **kwargs):
        return Context(sim, kwargs.get('pick'))

    def get_interaction_parameters(self):
        return {}

    def set_choices(self, *args):
        raise AssertionError('client choices touched')


class FakePump(object):
    def __init__(self):
        self.posted = []
        self.alive = True

    def post(self, fn, *args):
        if not self.alive:
            return False
        self.posted.append((fn, args))
        return True

    def drain(self):
        batch = self.posted[:]
        del self.posted[:]
        for fn, args in batch:
            fn(*args)
        return len(batch)

    def run(self, limit=200):
        for _ in range(limit):
            if not self.drain():
                return
        raise AssertionError('tick chain never settled')


class AvailabilityTests(unittest.TestCase):
    def setUp(self):
        for value in calls.values():
            del value[:]
        clock.__init__()
        choices._show_interaction_failure_reason = False
        script_object.logger = RealLogger()
        self.pump = FakePump()
        self.sim = types.SimpleNamespace(id=1, position=types.SimpleNamespace(x=0.0, y=0.0, z=0.0))
        world.sim = self.sim
        world.client = Client()
        world.objects = {}
        world.fire = None
        self.logs = []
        settings._stored['keyboard'] = True
        settings._stored['scanner'] = True
        patches = [patch.object(availability, 'pump', self.pump),
                   patch.object(availability, 'time', clock),
                   patch.object(speech, 'log_line', self.logs.append)]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        availability.reset()

    def add(self, *objs):
        for obj in objs:
            world.objects[obj.id] = obj
        return list(objs)

    def check(self, *objs):
        availability.begin(self.sim, self.add(*objs))
        self.pump.run()
        return [availability.state(obj) for obj in objs]

    # ---------------------------------------------------------- pie outcomes

    def test_three_outcomes_match_the_native_pie(self):
        usable = Obj(10, [row('grey', GREY), row('cook', PASS), row('never', PASS)])
        locked = Obj(11, [row('hidden', HIDDEN), row('needs_skill', GREY)])
        empty = Obj(12, [row('hidden', HIDDEN)])
        nothing = Obj(13)
        self.assertEqual(self.check(usable, locked, empty, nothing),
                         [availability.USABLE, availability.LOCKED, availability.EMPTY, availability.EMPTY])
        self.assertNotIn('never', calls['tests'])                 # short-circuits on the first usable row
        self.assertEqual(availability._verdicts[11][2], 'needs_skill')
        self.assertEqual(availability._verdicts[10][2], 'cook')

    def test_suppressed_and_non_user_directed_rows_are_hidden(self):
        suppressed = Obj(20, [row('sit', PASS)], suppress={'sit'})
        autonomous_only = Obj(21, [row('auto', PASS, user=False)])
        greyed_auto = Obj(22, [row('auto', GREY, user=False)])
        self.assertEqual(self.check(suppressed, autonomous_only, greyed_auto), [availability.EMPTY] * 3)

    def test_debug_failure_flag_shows_hidden_rows_greyed(self):
        choices._show_interaction_failure_reason = True
        self.assertEqual(self.check(Obj(23, [row('auto', PASS, user=False)])), [availability.LOCKED])

    def test_pie_mixers_follow_add_potential_aops(self):
        passing_mixer = Obj(30, [row('social_si', PASS, user=False, sub=[(Aop(Affordance('chat'), None), PASS)])])
        hidden_mixer = Obj(31, [row('social_si', PASS, user=False, sub=[(Aop(Affordance('m', user=False), None), PASS)])])
        greyed_parent = Obj(32, [row('greyed_si', GREY, user=False, sub=[(Aop(Affordance('m2'), None), PASS)])])
        self.assertEqual(self.check(passing_mixer, hidden_mixer, greyed_parent),
                         [availability.USABLE, availability.EMPTY, availability.LOCKED])
        self.assertEqual(availability._verdicts[30][2], 'chat')
        # a greyed parent's mixer is judged with the PARENT's failure, untested
        mixer_calls = [c for c in calls['valid'] if c[0] == 'm2']
        self.assertEqual(mixer_calls, [('m2', None, True, False)])

    def test_mixers_use_their_parents_target_context(self):
        seen = []

        class Recording(Affordance):
            def potential_pie_menu_sub_interactions_gen(self, target, context, scoring_gsi_handler=None, **kwargs):
                seen.append(context.pick.kwargs['target'])
                return iter([(Aop(Affordance('chat'), None), PASS)])
        piece = Obj(36)
        piece.aops = [Aop(Recording('social_si', user=False), PASS)]
        piece.aops[0].target = piece
        self.assertEqual(self.check(Obj(35, forwarded=[piece])), [availability.USABLE])
        self.assertEqual(seen, [piece])

    def test_mixers_only_walked_when_they_can_change_the_verdict(self):
        self.check(Obj(33, [row('grey_user', GREY), row('greyed_si', GREY, user=False, sub=[(Aop(Affordance('x'), None), PASS)])]))
        self.assertEqual(calls['sub'], [])                          # already locked; greyed mixers add nothing
        self.check(Obj(34, [row('ok', PASS), row('social_si', PASS, user=False)]))
        self.assertEqual(calls['sub'], [])                          # usable before any mixer walk

    def test_forwarded_pick_targets_are_included_with_their_own_suppression(self):
        piece = Obj(41, [row('sit_piece', PASS)])
        sofa = Obj(40, [row('hidden', HIDDEN)], forwarded=[piece, None])
        self.assertEqual(self.check(sofa), [availability.USABLE])
        self.assertIn(('sit_piece', piece, False, True), calls['valid'])
        # one pick and context per target, at the picked sofa's spot
        sofa_context, piece_context = calls['contexts'][-2:]
        self.assertIs(sofa_context.pick.kwargs['target'], sofa)
        self.assertIs(piece_context.pick.kwargs['target'], piece)
        self.assertIsNot(sofa_context, piece_context)
        self.assertEqual(piece_context.pick.kwargs['routing_surface'], 'surface-40')
        self.assertIs(piece_context.pick.kwargs['location'], sofa.position)
        self.assertEqual(piece_context.preferred_objects, {sofa})
        blocked_piece = Obj(43, [row('sit_piece', PASS)], suppress={'sit_piece'})
        self.assertEqual(self.check(Obj(42, forwarded=[blocked_piece])), [availability.EMPTY])

    def test_surface_providers_stay_listed_when_ordinary_rows_are_empty(self):
        pool, platform, ocean_edge = Obj(55), Obj(56), Obj(57)
        pool.provides_terrain_interactions = True
        platform.provided_routing_surface = 'platform'
        ocean_edge.provides_ocean_interactions = True
        self.assertEqual(self.check(pool, platform, ocean_edge), [availability.USABLE] * 3)
        self.assertFalse(availability._verdicts[55][3])             # a rule, not an error
        greyed_pool = Obj(58, [row('swim', GREY)])
        greyed_pool.provides_terrain_interactions = True
        self.assertEqual(self.check(greyed_pool), [availability.LOCKED])

    def test_fire_rows_keep_an_otherwise_empty_object_listed(self):
        asked = []
        world.fire = types.SimpleNamespace(
            fire_is_active=True,
            get_fires_in_potential_targets=lambda targets: asked.append(targets) or ['fire'])
        stove = Obj(59, forwarded=[Obj(60)])
        self.assertEqual(self.check(stove), [availability.USABLE])
        self.assertEqual([target.id for target, _ in asked[0]], [59, 60])
        self.assertEqual({surface for _, surface in asked[0]}, {'surface-59'})
        world.fire = types.SimpleNamespace(fire_is_active=True, get_fires_in_potential_targets=lambda targets: [])
        self.assertEqual(self.check(Obj(61)), [availability.EMPTY])
        world.fire = types.SimpleNamespace(fire_is_active=False, get_fires_in_potential_targets=None)
        self.assertEqual(self.check(Obj(62)), [availability.EMPTY])

    def test_context_mirrors_the_native_pie_request(self):
        obj = Obj(50, [row('use', PASS)])
        self.check(obj)
        pick = calls['picks'][-1]
        self.assertEqual(pick['pick_type'], 2)
        self.assertIs(pick['target'], obj)
        self.assertEqual((pick['lot_id'], pick['level'], pick['routing_surface']), (77, 1, 'surface-50'))
        context = calls['contexts'][-1]
        self.assertIs(context.sim, self.sim)
        self.assertIn(obj, context.preferred_objects)

    # ------------------------------------------------------------ fail-open

    def test_errors_keep_objects_listed_and_log_once(self):
        raising = Obj(60, [row('boom', None, raises=RuntimeError('bad test'))])
        swallowed = Obj(61, swallow=RuntimeError('bad affordance'))
        self.assertEqual(self.check(raising, swallowed), [availability.USABLE, availability.USABLE])
        self.assertTrue(availability._verdicts[60][3] and availability._verdicts[61][3])
        self.assertIn('swallowed', availability._verdicts[61][2])
        self.assertEqual(calls['real_log'], [])                    # our probe raised no error report
        self.assertIs(type(script_object.logger), RealLogger)      # logger restored
        clock.mono += availability.RECHECK_SECONDS
        self.check(raising, swallowed)
        failures = [line for line in self.logs if 'check failed' in line]
        self.assertEqual(len(failures), 2)                         # once per object per Sim

    def test_a_player_click_after_a_probe_still_reports(self):
        self.check(Obj(62, swallow=RuntimeError('x')))
        list(Obj(63, swallow=RuntimeError('y')).potential_interactions(None))
        self.assertEqual(calls['real_log'], ['Exception while generating'])

    def test_lookup_error_does_not_stall_the_queue(self):
        good = Obj(71, [row('use', PASS)])
        availability.begin(self.sim, self.add(Obj(70), good))
        boom = types.SimpleNamespace(get=lambda obj_id: (_ for _ in ()).throw(RuntimeError('mgr')) if obj_id == 70 else world.objects.get(obj_id))
        with patch.object(services, 'object_manager', lambda: boom):
            self.pump.run()
        self.assertEqual(availability.state(70), availability.USABLE)
        self.assertEqual(availability.state(good), availability.USABLE)

    def test_vanished_objects_count_against_the_budget(self):
        clock.test_cost = 0.0

        class Ticking(object):
            def get(self, obj_id):
                clock.perf += 0.001
                return None
        availability.begin(self.sim, [Obj(200 + i) for i in range(50)])
        with patch.object(services, 'object_manager', lambda: Ticking()):
            self.pump.drain()
        self.assertEqual(len(availability._queue), 46)             # 4 lookups use the 4 ms, the rest wait
        self.assertEqual(len(self.pump.posted), 1)

    def test_pending_until_checked_and_unknown_ids_pending(self):
        obj = Obj(80, [row('hidden', HIDDEN)])
        availability.begin(self.sim, self.add(obj))
        self.assertEqual(availability.state(obj), availability.PENDING)
        self.assertEqual(availability.state(999), availability.PENDING)
        self.assertEqual(availability.state(None), availability.PENDING)
        self.pump.run()
        self.assertEqual(availability.state(obj), availability.EMPTY)

    def test_pump_unavailable_leaves_everything_pending_and_retries(self):
        self.pump.alive = False
        obj = Obj(81, [row('use', PASS)])
        availability.begin(self.sim, self.add(obj))
        self.assertEqual(self.pump.posted, [])
        self.assertEqual(availability.state(obj), availability.PENDING)
        self.pump.alive = True
        availability.state(obj)                                     # any call re-arms
        self.pump.run()
        self.assertEqual(availability.state(obj), availability.USABLE)

    # --------------------------------------------------------- budget/ticks

    def test_budget_pauses_inside_one_object_and_resumes(self):
        clock.test_cost = 0.003
        heavy = Obj(90, [row('r{}'.format(i), HIDDEN) for i in range(5)] + [row('last', PASS)])
        light = Obj(91, [row('use', PASS)])
        availability.begin(self.sim, self.add(heavy, light))
        self.assertEqual(self.pump.drain(), 1)
        self.assertEqual(len(calls['tests']), 2)                   # setup step + 2 tests fit 4 ms
        self.assertEqual(availability.state(heavy), availability.PENDING)
        self.pump.run()
        self.assertEqual(availability.state(heavy), availability.USABLE)
        self.assertEqual(calls['tests'].count('r0'), 1)            # resumed, never restarted

    def test_one_slow_native_test_still_ends_the_tick(self):
        clock.test_cost = 0.050
        objs = [Obj(100 + i, [row('slow', PASS)]) for i in range(3)]
        availability.begin(self.sim, self.add(*objs))
        self.pump.drain()
        self.assertEqual(len(calls['tests']), 1)
        self.assertGreaterEqual(availability._run['max_step_ms'], 50.0)

    def test_row_cap_keeps_a_runaway_object_listed(self):
        with patch.object(availability, 'MAX_STEPS', 5):
            self.assertEqual(self.check(Obj(110, [row('r{}'.format(i), HIDDEN) for i in range(20)])),
                             [availability.USABLE])
        self.assertIn('over 5 rows', availability._verdicts[110][2])

    def test_superseded_tick_does_no_work(self):
        clock.test_cost = 0.005                                     # one object fills a tick
        first = Obj(120, [row('first', PASS)])
        second = Obj(122, [row('second', PASS)])
        availability.begin(self.sim, self.add(first, second))
        clock.mono += 1.0                                           # the first post looks lost
        availability.state(first)
        self.assertEqual(len(self.pump.posted), 2)
        self.pump.drain()                                           # both land in one drain
        self.assertEqual(calls['tests'], ['first'])               # only the newest tick worked

    def test_rearm_waits_before_reposting(self):
        availability.begin(self.sim, self.add(Obj(121, [row('use', PASS)])))
        availability.state(121)
        clock.mono += 0.2
        availability.state(121)
        self.assertEqual(len(self.pump.posted), 1)

    def test_reset_cancels_queued_and_in_progress_work(self):
        clock.test_cost = 0.003
        heavy = Obj(130, [row('r{}'.format(i), HIDDEN) for i in range(6)])
        availability.begin(self.sim, self.add(heavy, Obj(131, [row('use', PASS)])))
        self.pump.drain()
        tested = len(calls['tests'])
        availability.reset()
        self.pump.run()
        self.assertEqual(len(calls['tests']), tested)
        self.assertEqual(availability.state(heavy), availability.PENDING)

    def test_settings_off_cancels_at_the_next_tick(self):
        availability.begin(self.sim, self.add(Obj(140, [row('use', PASS)])))
        settings._stored['scanner'] = False
        self.pump.run()
        self.assertEqual(calls['tests'], [])
        self.assertEqual(availability._queue, [])

    # ------------------------------------------------------- Sim and cache

    def test_sim_change_in_begin_drops_verdicts(self):
        obj = Obj(150, [row('hidden', HIDDEN)])
        self.check(obj)
        self.assertEqual(availability.state(obj), availability.EMPTY)
        other = types.SimpleNamespace(id=2, position=self.sim.position)
        availability.begin(self.sim, [obj])                        # nothing queued: fresh
        world.sim = other
        availability.begin(other, [obj])
        self.assertEqual(availability.state(obj), availability.PENDING)

    def test_active_sim_changing_under_a_tick_forgets_everything(self):
        obj = Obj(151, [row('use', PASS)])
        availability.begin(self.sim, self.add(obj))
        world.sim = types.SimpleNamespace(id=9)
        before = availability.revision()
        self.pump.run()
        self.assertEqual(calls['tests'], [])
        self.assertEqual(availability.state(obj), availability.PENDING)
        self.assertGreater(availability.revision(), before)

    def test_callback_resets_like_the_client_calls_it(self):
        self.check(Obj(152, [row('use', PASS)]))
        availability.on_active_sim_changed(self.sim, types.SimpleNamespace(id=3))
        self.assertEqual(availability.state(152), availability.PENDING)

    def test_same_sim_recheck_keeps_last_verdict_and_orders_new_first(self):
        old = Obj(160, [row('hidden', HIDDEN)])
        self.check(old)
        clock.mono += availability.RECHECK_SECONDS
        new = Obj(161, [row('use', PASS)])
        availability.begin(self.sim, self.add(new, old))
        self.assertEqual(availability._queue, [161, 160])
        self.assertEqual(availability.state(old), availability.EMPTY)   # no flicker while rechecked
        fresh = Obj(162, [row('use', PASS)])
        clock.mono += 1.0
        availability.begin(self.sim, self.add(fresh, old))
        self.assertNotIn(161, availability._queue)                # left the scan: not checked

    def test_recheck_keeps_verdicts_and_requeues(self):
        obj = Obj(165, [row('hidden', HIDDEN)])
        self.check(obj)
        availability.recheck()
        availability.begin(self.sim, [obj])
        self.assertEqual(availability._queue, [165])
        self.assertEqual(availability.state(obj), availability.EMPTY)
        obj.aops = [row('use', PASS)]
        self.pump.run()
        self.assertEqual(availability.state(obj), availability.USABLE)

    def test_revision_bumps_only_when_what_the_scanner_shows_changes(self):
        usable = Obj(170, [row('use', PASS)])
        availability.begin(self.sim, self.add(usable))
        start = availability.revision()
        self.pump.run()
        self.assertEqual(availability.revision(), start)            # pending and usable look the same
        availability.begin(self.sim, self.add(Obj(171, [row('grey', GREY)])))
        start = availability.revision()
        self.pump.run()
        self.assertEqual(availability.revision(), start + 1)
        values = [availability.revision()]
        availability.invalidate([171])
        values.append(availability.revision())
        availability.reset()
        values.append(availability.revision())
        self.assertEqual(values, sorted(set(values)))               # monotonic across reset

    # ------------------------------------------------- v14q pause/backoff

    def test_pause_keeps_verdicts_and_cancels_work(self):
        clock.test_cost = 0.003
        done = Obj(300, [row('hidden', HIDDEN)])
        self.check(done)
        heavy = Obj(301, [row('r{}'.format(i), HIDDEN) for i in range(6)])
        availability.begin(self.sim, self.add(done, heavy))
        self.pump.drain()                                           # heavy is part-way through
        tested = len(calls['tests'])
        before = availability.revision()
        availability.pause()
        self.pump.run()
        self.assertEqual(len(calls['tests']), tested)               # nothing ran after the pause
        self.assertEqual(availability.revision(), before)           # the list did not change
        self.assertEqual(availability.state(done), availability.EMPTY)
        availability.begin(self.sim, [done, heavy])                 # back from a long dialog
        self.assertEqual(availability._queue, [301])                # only the unfinished one
        self.assertEqual(availability.state(done), availability.EMPTY)

    def test_stable_verdicts_back_off_and_slow_objects_wait_longer(self):
        obj = Obj(310, [row('hidden', HIDDEN)])
        waits = []
        for _ in range(5):
            self.check(obj)
            verdict = availability._verdicts[310]
            waits.append(verdict[5] - verdict[1])
            clock.mono = verdict[5]
        self.assertEqual(waits, [10.0, 20.0, 40.0, 60.0, 60.0])
        clock.test_cost = 0.020                                     # a 20 ms native step
        slow = Obj(311, [row('heavy', HIDDEN)])
        self.check(slow)
        verdict = availability._verdicts[311]
        self.assertEqual(verdict[5] - verdict[1], 20.0)
        self.assertGreaterEqual(verdict[6], availability.SLOW_STEP_MS)

    def test_a_change_or_an_error_restarts_the_short_interval(self):
        obj = Obj(320, [row('hidden', HIDDEN)])
        self.check(obj)
        clock.mono = availability._verdicts[320][5]
        self.check(obj)
        self.assertEqual(availability._verdicts[320][4], 2)
        obj.aops = [row('use', PASS)]
        clock.mono = availability._verdicts[320][5]
        self.check(obj)
        self.assertEqual(availability._verdicts[320][4], 1)
        obj.aops = [row('boom', None, raises=RuntimeError('x'))]
        streaks = []
        for _ in range(3):
            clock.mono = availability._verdicts[320][5]
            self.check(obj)
            streaks.append(availability._verdicts[320][4])
        self.assertEqual(streaks, [1, 2, 3])                        # into error resets, same error backs off

    def test_recheck_makes_everything_due_but_keeps_the_streak(self):
        obj = Obj(330, [row('hidden', HIDDEN)])
        self.check(obj)
        clock.mono = availability._verdicts[330][5]
        self.check(obj)
        availability.recheck()
        self.assertEqual(availability._verdicts[330][4], 2)
        availability.begin(self.sim, [obj])
        self.assertEqual(availability._queue, [330])

    def test_run_log_names_the_slowest_step_and_is_rate_limited(self):
        fast = Obj(340, [row('fine', HIDDEN)])
        slow = Obj(341, [row('quick', HIDDEN), Aop(Affordance('crafting_heavy'), HIDDEN)])
        slow.aops[1].target = slow
        costs = {'crafting_heavy': 0.030}
        original = Aop.test

        def timed(aop, context):
            clock.perf += costs.get(aop.affordance.__name__, 0.0)
            return original(aop, context)
        with patch.object(Aop, 'test', timed):
            self.check(fast, slow)
        lines = [line for line in self.logs if line.startswith('availability: checked')]
        self.assertEqual(len(lines), 1)
        self.assertIn('1 steps over 16 ms', lines[0])
        self.assertIn('slowest at 341 def341 rows crafting_heavy', lines[0])
        clock.mono = max(v[5] for v in availability._verdicts.values())
        with patch.object(Aop, 'test', timed):
            self.check(fast, slow)                                  # same picture, too soon
        self.assertEqual(len([l for l in self.logs if l.startswith('availability: checked')]), 1)
        clock.mono += availability._LOG_SECONDS
        slow.aops = [row('now_usable', PASS)]
        self.check(fast, slow)                                      # the picture changed
        self.assertEqual(len([l for l in self.logs if l.startswith('availability: checked')]), 2)

    def test_sim_change_logs_its_first_summary_at_once(self):
        obj = Obj(360, [row('hidden', HIDDEN)])
        self.check(obj)
        other = types.SimpleNamespace(id=5, position=self.sim.position)
        world.sim = other
        availability.begin(other, [obj])
        self.pump.run()
        lines = [l for l in self.logs if l.startswith('availability: checked')]
        self.assertEqual(len(lines), 2)
        self.assertIn('for sim 5', lines[1])

    # ------------------------------------------------- v14s UI and retention

    def set_flags(self, modal=False, editing=False, menu=False):
        keys = types.SimpleNamespace(_modal_active=modal, _editing_active=editing)
        scanner = types.SimpleNamespace(_menu_open=menu)
        patcher = patch.dict(sys.modules, {'tyjokr_a11y_keys': keys, 'tyjokr_a11y_scanner': scanner})
        patcher.start()
        self.addCleanup(patcher.stop)
        return keys, scanner

    def test_queued_tick_yields_to_a_dialog_the_console_or_a_scanner_menu(self):
        known = Obj(400, [row('hidden', HIDDEN)])
        self.check(known)
        for flags in ({'modal': True}, {'editing': True}, {'menu': True}):
            keys, scanner = self.set_flags(**flags)
            clock.mono = availability._verdicts[400][5]
            waiting = Obj(401 + len(calls['tests']), [row('use', PASS)])
            availability.begin(self.sim, self.add(known, waiting))
            before = (list(calls['tests']), availability.revision())
            self.pump.run()
            self.assertEqual((calls['tests'], availability.revision()), before)   # no native step, no change
            self.assertEqual(availability._queue, [])
            self.assertEqual(availability.state(known), availability.EMPTY)       # verdict kept
            self.assertEqual(availability.state(waiting), availability.PENDING)
            keys._modal_active = keys._editing_active = scanner._menu_open = False
            availability.begin(self.sim, [known, waiting])                          # the next scan resumes
            self.pump.run()
            self.assertEqual(availability.state(waiting), availability.USABLE)

    def test_a_dialog_opening_mid_object_drops_only_that_check(self):
        clock.test_cost = 0.003
        keys, _ = self.set_flags()
        heavy = Obj(410, [row('r{}'.format(i), HIDDEN) for i in range(6)] + [row('last', PASS)])
        availability.begin(self.sim, self.add(heavy))
        self.pump.drain()
        partial = len(calls['tests'])
        self.assertGreater(partial, 0)
        keys._modal_active = True
        self.pump.run()
        self.assertEqual(len(calls['tests']), partial)
        keys._modal_active = False
        availability.begin(self.sim, [heavy])
        self.pump.run()
        self.assertEqual(availability.state(heavy), availability.USABLE)

    def test_no_keys_module_means_not_busy(self):
        with patch.dict(sys.modules):
            sys.modules.pop('tyjokr_a11y_keys', None)
            sys.modules.pop('tyjokr_a11y_scanner', None)
            self.assertFalse(availability._ui_busy())

    def test_verdicts_outside_the_scan_are_capped_oldest_first(self):
        with patch.object(availability, '_VERDICT_LIMIT', 3):
            objs = [Obj(420 + i, [row('hidden', HIDDEN)]) for i in range(5)]
            for obj in objs:
                clock.mono += 1.0
                self.check(obj)                                     # each scan holds one object
            # 424 is in the scan; at most 3 others are kept, the oldest went
            self.assertEqual(sorted(availability._verdicts), [421, 422, 423, 424])

    def test_walking_back_in_range_shows_the_last_verdict_at_once(self):
        far = Obj(440, [row('hidden', HIDDEN)])
        near = Obj(441, [row('use', PASS)])
        self.check(far, near)
        availability.begin(self.sim, [near])                        # far left the range
        availability.begin(self.sim, [near, far])                   # and came back
        self.assertEqual(availability.state(far), availability.EMPTY)
        self.assertNotIn(440, availability._queue)                  # not due yet, no recheck

    def test_counts_cover_the_current_scan_only(self):
        self.check(Obj(430, [row('use', PASS)]), Obj(431, [row('hidden', HIDDEN)]))
        availability.begin(self.sim, [world.objects[430]])
        self.assertIn('usable 1 locked 0 empty 0', availability.status())

    def test_mixer_phase_is_attributed(self):
        costs = {'social_si': 0.025}

        class Heavy(Affordance):
            def potential_pie_menu_sub_interactions_gen(self, target, context, scoring_gsi_handler=None, **kwargs):
                clock.perf += costs['social_si']
                return iter([(Aop(Affordance('m', user=False), None), PASS)])
        obj = Obj(350)
        obj.aops = [Aop(Heavy('social_si', user=False), PASS)]
        obj.aops[0].target = obj
        self.check(obj)
        line = [l for l in self.logs if l.startswith('availability: checked')][-1]
        self.assertIn('slowest at 350 def350 mixers social_si', line)

    def test_begin_never_raises(self):
        class Bad(object):
            @property
            def id(self):
                raise RuntimeError('gone')
        self.assertIsInstance(availability.begin(self.sim, [Bad()]), int)
        self.assertIsInstance(availability.begin(self.sim, None), int)

    def test_diagnostic_command_lists_nearest(self):
        self.check(Obj(180, [row('use', PASS)]), Obj(181, [row('hidden', HIDDEN)]))
        lines = []
        with patch.object(env.commands, 'CheatOutput', lambda connection: lines.append):
            availability.a11y_availability()
        self.assertIn('usable 1', lines[0])
        self.assertIn('def180 usable use', lines[1])

    def test_source_has_no_dashes(self):
        with open(availability.__file__, encoding='utf-8') as handle:
            text = handle.read()
        self.assertNotIn(chr(0x2014), text)
        self.assertNotIn(chr(0x2013), text)


if __name__ == '__main__':
    unittest.main()
