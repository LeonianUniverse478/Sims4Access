"""Offline suite for the speech module: modes, read key, progressive reads,
widget dedupe guards. Runs against a BUILT ts4script zip (3.7 bytecode), so
run with:  py -3.7 test_speech_modes.py [path-to-ts4script]

Default target is the deployed dev build in Mods. No audio: the backend is
forced to log-only and the beep is mocked (if a real beep sounds during a
run, the mock has been lost).
"""
import os
import sys
import tempfile
import time

DEFAULT_ZIP = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'Scripts')
target = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_ZIP
assert os.path.exists(target), 'no built script at {}'.format(target)
sys.path.insert(0, target)

import tyjokr_a11y_settings as settings   # noqa: E402
import tyjokr_a11y_speech as speech       # noqa: E402

# Never touch the real cfg from tests.
_TMP = tempfile.mkdtemp(prefix='a11y_test_')
settings.PATH = os.path.join(_TMP, 'test.cfg')
settings._JSON_PATH = os.path.join(_TMP, 'test.json')

speech._backend_name = 'log-only'   # no SAPI child, no audio
speech.log_enabled = False


class _FakeNVDA(object):
    """NVDA client DLL loaded, NVDA NOT running: every call reports the
    error code that made stop() silence the wrong backend (2026-08-03)."""

    def __init__(self):
        self.cancels = 0
        self.speaks = 0

    def nvdaController_cancelSpeech(self):
        self.cancels += 1
        return 1        # nonzero = NVDA is not running

    def nvdaController_speakText(self, _text):
        self.speaks += 1
        return 1


class _FakeSapi(object):
    """Stands in for the PowerShell child: records the interrupt/queue
    bytes the module writes to its stdin."""

    def __init__(self):
        self.lines = []

    class _Stdin(object):
        def __init__(self, owner):
            self.owner = owner

        def write(self, data):
            self.owner.lines.append(data)

        def flush(self):
            pass

    @property
    def stdin(self):
        return _FakeSapi._Stdin(self)

SPOKEN = []      # (source, interrupt_flag, text) from SPEAK log lines
CAPTURED = []    # texts from CAPTURE log lines
STOPS = []
BEEPS = []


def _fake_log(message):
    if message.startswith('SPEAK['):
        tag, _, text = message[6:].partition(']: ')
        SPOKEN.append((tag[:-2], tag[-1] == 'i', text))
    elif message.startswith('CAPTURE['):
        CAPTURED.append(message.partition(']: ')[2])


speech.log_line = _fake_log
speech._beep = lambda: BEEPS.append(1)
_real_stop = speech.stop


def _fake_stop():
    STOPS.append(1)
    _real_stop()


speech.stop = _fake_stop


def reset(mode='hover'):
    speech._busy_until = 0.0
    speech._cancel_deferred()
    with speech._speech_lock:
        speech._pending.clear()
    time.sleep(0.25)   # let any pending flush timer die out
    with speech._speech_lock:
        speech._pending.clear()
    speech._captured_text = None
    speech._captured_time = 0.0
    speech._last_repeated = None
    speech._last_text = None
    speech._last_time = 0.0
    speech._last_source = None
    speech._last_accept_time = 0.0
    speech.speech_mode = mode
    del SPOKEN[:]
    del CAPTURED[:]
    del STOPS[:]
    del BEEPS[:]


def spoken_texts():
    return [text for _s, _i, text in SPOKEN]


PASS = 0


def ok(cond, label):
    global PASS
    assert cond, 'FAIL: ' + label
    PASS += 1
    print('  ok - ' + label)


# ---------------------------------------------------------------- hover stop
print('read key stops, second press re-reads (hover mode):')
reset()
speech.speak('Fishing. 4', source='widget')
ok(spoken_texts() == ['Fishing. 4'], 'auto-spoken in hover mode')
speech.repeat_last()
ok(STOPS == [1], 'first press stops')
ok(speech._last_repeated is None, 'stop re-arms the key')
speech.repeat_last()
ok(spoken_texts() == ['Fishing. 4', 'Fishing. 4'], 'second press re-reads')
speech.repeat_last()
ok(STOPS == [1, 1], 'third press stops again')

# ------------------------------------------- press in silence = read, not stop
print('read key re-reads instead of a soundless stop once speech has ended:')
reset()
speech.speak('Fishing. 4', source='widget')
ok(speech._probably_still_speaking(), 'audio is considered playing right after')
# Simulate real elapsed time: the audio has finished AND the identical-text
# dedupe window has expired (both are >= 1s, so they lapse together).
speech._busy_until = 0.0
speech._last_time -= 5.0
speech.repeat_last()
ok(STOPS == [], 'press in silence does not do a soundless stop')
ok(spoken_texts() == ['Fishing. 4', 'Fishing. 4'], 'press in silence re-reads')
speech.repeat_last()
ok(STOPS == [1], 'press during the re-read stops it')

print('queued speech stays "playing" until the utterance ahead of it ends:')
reset()
speech.speak('Charisma. 3', source='widget')
busy_after_label = speech._busy_until
speech._last_accept_time = time.monotonic() - 1.0
speech.speak('A long description of the charisma skill goes here.',
             source='tooltip')
ok(speech._busy_until > busy_after_label,
   'queued tooltip extends the busy window past the label it waits behind')

# ------------------------------------------------- numpad-8 progressive bug
print('read key STOPS during a progressive read (the shipped numpad-8 bug):')
reset()
speech.speak_progressive('Sat. 2:35 AM', 'Spring Day 14 of 14. Sunny. 21', delay=5.0)
ok(spoken_texts() == ['Sat. 2:35 AM'], 'head speaks at once')
ok(speech._captured_text == 'Sat. 2:35 AM. Spring Day 14 of 14. Sunny. 21',
   'capture is head + body')
speech.repeat_last()
ok(STOPS == [1], 'press during head playback stops (was: re-read full text)')
ok(len(spoken_texts()) == 1, 'nothing new was spoken by the stop press')
speech.repeat_last()
ok(spoken_texts()[-1] == 'Sat. 2:35 AM. Spring Day 14 of 14. Sunny. 21',
   'second press reads head and body together')

# ----------------------------------------------------- progressive deferral
print('progressive body flushes after the delay, then the key stops:')
reset()
speech.speak_progressive('Head line', 'Long body text here', delay=0.05)
time.sleep(0.3)
ok(spoken_texts() == ['Head line', 'Long body text here'],
   'body speaks after the delay')
speech.repeat_last()
ok(STOPS == [1], 'after hearing it all, the key stops')

reset()
speech.speak_progressive('Head line', 'Long body text here', delay=0.05)
speech.speak('Another control', source='widget')
time.sleep(0.3)
ok('Long body text here' not in spoken_texts(),
   'a new utterance cancels the held-back body')

# -------------------------------------------------- progressive manual mode
print('progressive in manual mode captures silently:')
reset('manual')
speech.speak_progressive('Head line', 'Body text', delay=0.05)
time.sleep(0.2)
ok(spoken_texts() == [], 'nothing auto-spoken in manual mode')
speech.repeat_last()
ok(spoken_texts() == ['Head line. Body text'], 'read key speaks the capture')

# ------------------------------------------------- head_spoken (time panel)
print('head_spoken variant defers only the body (time panel):')
reset()
speech.speak('Sat. 2:35 AM', source='widget')
speech.speak_progressive('Sat. 2:35 AM', 'Spring Day 14 of 14', delay=0.05,
                         head_spoken=True)
ok(spoken_texts() == ['Sat. 2:35 AM'], 'head is not spoken twice')
time.sleep(0.3)
ok(spoken_texts() == ['Sat. 2:35 AM', 'Spring Day 14 of 14'],
   'pop-up body arrives after the delay')
speech.repeat_last()
ok(STOPS == [1], 'read key stops after the full sequence')
speech.repeat_last()
ok(spoken_texts()[-1] == 'Sat. 2:35 AM. Spring Day 14 of 14',
   'second press reads panel line and pop-up together')

# ------------------------------------- widget label-only repeat suppression
print('a bare label cannot interrupt or evict a richer widget line:')
reset()
speech.speak('Hunger. 80%', source='widget')
speech._last_accept_time = time.monotonic() - 1.0   # outside the burst gap
speech.speak('Hunger', source='widget')
ok(spoken_texts() == ['Hunger. 80%'], 'label-only repeat is not spoken')
ok(speech._last_repeated == 'Hunger. 80%', 'read key still armed on rich line')
ok(speech._captured_text == 'Hunger. 80%', 'capture keeps the richer line')

reset()
speech._last_accept_time = time.monotonic()          # force parking
speech.speak('Fishing. 4', source='widget')
speech.speak('Fishing', source='widget')
time.sleep(0.3)
ok(spoken_texts() == ['Fishing. 4'],
   'parked richer line survives newest-wins against its own label')

reset()
speech.speak('Hunger. 80%', source='widget')
speech._last_accept_time = time.monotonic() - 1.0
speech.speak('Energy. 50%', source='widget')
ok(spoken_texts() == ['Hunger. 80%', 'Energy. 50%'],
   'a different control still speaks (no over-suppression)')

reset()
speech.speak('Hunger', source='widget')
speech._last_accept_time = time.monotonic() - 1.0
speech.speak('Hunger. 80%', source='widget')
ok(spoken_texts() == ['Hunger', 'Hunger. 80%'],
   'a richer line after its label still speaks')

# --------------------------------------------------------- request_hush
print('request_hush spares fresh widget speech:')
reset()
speech.speak('Fishing. 4', source='widget')
speech.request_hush()
ok(STOPS == [], 'no stop while the row label is fresh')
speech._last_time -= 2.0
speech.request_hush()
ok(STOPS == [1], 'stale speech is still hushed')

reset()
speech._last_accept_time = time.monotonic()
speech.speak('Fishing. 4', source='widget')     # parked
speech._last_time = 0.0
speech.request_hush()
ok(STOPS == [], 'no stop while a widget line is parked')
time.sleep(0.3)
ok(spoken_texts() == ['Fishing. 4'], 'parked line still flushed')

# --------------------------------------------------------- modes: beeps/off
print('beeps and off modes:')
reset('beeps')
speech.speak('Fishing. 4', source='widget')
ok(spoken_texts() == [] and BEEPS == [1], 'beeps mode: tone, no speech')
ok(CAPTURED == ['Fishing. 4'], 'beeps mode still captures')
speech.repeat_last()
ok(spoken_texts() == ['Fishing. 4'], 'read key talks in beeps mode')

reset('off')
speech.speak('Fishing. 4', source='widget')
speech.repeat_last()
ok(spoken_texts() == [] and STOPS == [], 'off mode: fully silent')

# ------------------------------------------------------- tooltip dedupe
print('tooltip queues and dedupes behind a widget line:')
reset()
speech.speak('Charisma. 3', source='widget')
speech._last_accept_time = time.monotonic() - 1.0
speech.speak('Charisma. 3. Level up by socializing.', source='tooltip')
ok(SPOKEN[-1][2] == 'Level up by socializing.',
   'leading segments just heard are stripped from the tooltip')
ok(SPOKEN[-1][1] is False, 'tooltip queues (no interrupt) after a widget line')

# ------------------------------------------- stop() reaches the live backend
# The shipped bug: the NVDA client DLL always loads, so the backend is named
# "nvda" even with NVDA not running, and every utterance actually came out of
# the SAPI child. stop() fired nvdaController_cancelSpeech and returned, so
# nothing was ever silenced -- the read key looked dead and the next press
# restarted the text ("needs two presses", 2026-08-03).
print('stop() silences the backend that is really speaking:')
reset()
_saved_backend, _saved_prism, _saved_sapi = (
    speech._backend_name, speech._prism, speech._sapi_proc)
speech.stop = _real_stop            # exercise the real one here
fake_nvda, fake_sapi = _FakeNVDA(), _FakeSapi()
fake_nvda.stop = lambda: fake_nvda.nvdaController_cancelSpeech() == 0
speech._backend_name = 'prism'
speech._prism = fake_nvda
speech._sapi_proc = fake_sapi
try:
    speech._real_stop_probe = True
    speech.stop()
    ok(fake_nvda.cancels == 1, 'NVDA cancel is still attempted first')
    ok(fake_sapi.lines == [b'I\n'],
       'stop falls through to the SAPI child that is actually speaking')

    # A fallback may still be speaking when the reader starts: stop both.
    fake_sapi.lines = []
    fake_nvda.nvdaController_cancelSpeech = lambda: 0     # 0 = NVDA is live
    speech.stop()
    ok(fake_sapi.lines == [b'I\n'], 'stop also silences fallback after reader switches')
finally:
    speech._backend_name, speech._prism, speech._sapi_proc = (
        _saved_backend, _saved_prism, _saved_sapi)
    speech.stop = _fake_stop

print('')
print('ALL {} CHECKS PASSED'.format(PASS))
