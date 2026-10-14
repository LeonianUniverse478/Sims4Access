"""Offline suite for the settings module: cfg parsing and hardening.
Runs against a BUILT ts4script zip (3.7 bytecode):
    py -3.7 test_settings_cfg.py [path-to-ts4script]
Never touches the real cfg: PATH is redirected to a temp folder.
"""
import os
import sys
import tempfile

DEFAULT_ZIP = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'Scripts')
target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ZIP
assert os.path.exists(target), 'no built script at {}'.format(target)
sys.path.insert(0, target)

import tyjokr_a11y_settings as settings   # noqa: E402

TMP = tempfile.mkdtemp(prefix='a11y_cfg_test_')
settings.PATH = os.path.join(TMP, 'test.cfg')
# Exercise automatic creation as in the game, even when testing source files.
settings._IN_GAME = True

PASS = 0


def ok(cond, label):
    global PASS
    assert cond, 'FAIL: ' + label
    PASS += 1
    print('  ok - ' + label)


def write_cfg(text):
    with open(settings.PATH, 'w', encoding='utf-8') as handle:
        handle.write(text)


def fresh(text=None):
    if os.path.isfile(settings.PATH):
        os.remove(settings.PATH)
    if text is not None:
        write_cfg(text)
    settings.reload()


print('value parsing:')
fresh("""[features]
sim actions = yes
object names = OFF
keyboard = 1
[speech]
mode = Beeps
braille = FULL
logging = true
[voice]
rate = 25
volume = -5
name = David
[behavior]
auto focus = on
""")
ok(settings.get('sim_actions') is True, 'yes -> True')
ok(settings.get('object_names') is False, 'OFF -> False')
ok(settings.get('keyboard') is True, '1 -> True')
ok(settings.get('speech_mode') == 'beeps', 'mode case-folded')
ok(settings.get('braille_mode') == 'full', 'braille case-folded')
ok(settings.get('sapi_rate') == 10, 'rate clamped to 10')
ok(settings.get('sapi_volume') == 0, 'volume clamped to 0')
ok(settings.get('sapi_voice') == 'David', 'voice kept verbatim')
ok(settings.get('auto_focus') is True, 'auto focus on')
ok(settings.load_errors == [], 'no spurious warnings')

print('tooltip delay parsing:')
fresh("[speech]\ntooltip delay = 2.5\n")
ok(abs(settings.get('tooltip_delay') - 2.5) < 1e-9, 'fractional seconds kept')
fresh("[speech]\ntooltip delay = 0\n")
ok(settings.get('tooltip_delay') == 0, '0 disables the delay')
fresh("[speech]\ntooltip delay = 99\n")
ok(settings.get('tooltip_delay') == 10, 'clamped to 10 seconds')
fresh("[speech]\ntooltip delay = -4\n")
ok(settings.get('tooltip_delay') == 0, 'negative clamped to 0')
fresh("[speech]\ntooltip delay = soon\n")
ok(settings.get('tooltip_delay') == 1.5, 'non-number keeps the default')
ok(any('tooltip delay' in err for err in settings.load_errors),
   'bad tooltip delay reported')
fresh(None)
settings.set('tooltip_delay', 2.0)
with open(settings.PATH, 'r', encoding='utf-8') as handle:
    ok('tooltip delay = 2\n' in handle.read(),
       'whole seconds render without a trailing .0')

print('legacy speech mode names:')
fresh("[speech]\nmode = talk\n")
ok(settings.get('speech_mode') == 'hover', 'talk -> hover')
fresh("[speech]\nmode = ondemand\n")
ok(settings.get('speech_mode') == 'manual', 'ondemand -> manual')

print('bad values keep defaults and warn:')
fresh("""[features]
sim actions = maybe
[speech]
mode = shouting
braille = dots
[voice]
rate = fast
""")
ok(settings.get('sim_actions') is True, 'bad bool -> default')
ok(settings.get('speech_mode') == 'hover', 'bad mode -> default')
ok(settings.get('braille_mode') == 'concise', 'bad braille -> default')
ok(settings.get('sapi_rate') == 3, 'non-number rate -> default')
ok(len(settings.load_errors) == 4, 'each bad value reported once')

print('broken lines are skipped, the rest still parses:')
fresh("""[features]
sim actions on
keyboard = off
""")
ok(settings.get('keyboard') is False, 'good line after bad line parses')
ok(any('skipped' in err for err in settings.load_errors), 'bad line reported')

print('duplicates, spacing and case in section/option names:')
fresh("""[ FEATURES ]
Sim  Actions = off
sim actions = on
""")
ok(settings.get('sim_actions') is True, 'last duplicate wins, names normalized')

print('empty value leaves the default in place:')
fresh("[voice]\nname =\n")
ok(settings.get('sapi_voice') == 'zira', 'empty option -> default')

print('missing file materializes defaults (in-game path):')
fresh(None)
ok(os.path.isfile(settings.PATH), 'cfg auto-created')
ok(settings.get('speech_mode') == 'hover', 'defaults active')

print('legacy JSON store fully removed (2026-08-16, never shipped):')
ok(not hasattr(settings, '_JSON_PATH'), 'no _JSON_PATH constant')
ok(not hasattr(settings, '_load_legacy_json'), 'no legacy loader')

print('set() writes through and survives reload:')
fresh(None)
settings.set('sapi_volume', 42)
settings.set('sim_actions', True)
settings.reload()
ok(settings.get('sapi_volume') == 42, 'volume persisted')
ok(settings.get('sim_actions') is True, 'bool persisted')
with open(settings.PATH, 'r', encoding='utf-8') as handle:
    content = handle.read()
ok('volume = 42' in content and 'sim actions = on' in content,
   'file regenerated with friendly words')

print('render_default is complete:')
rendered = settings.render_default()
ok('{' not in rendered, 'no unfilled placeholders')
ok('mode = hover' in rendered, 'default mode rendered')

print('unreadable file reports instead of raising:')
fresh(None)
with open(settings.PATH, 'wb') as handle:
    handle.write(b'[features]\nsim actions = \xff\xfe garbage \x81\n')
settings.reload()
ok(any('unreadable' in err for err in settings.load_errors),
   'undecodable cfg reported, no crash')
ok(settings.get('speech_mode') == 'hover', 'defaults still served')

print('')
print('ALL {} CHECKS PASSED'.format(PASS))
