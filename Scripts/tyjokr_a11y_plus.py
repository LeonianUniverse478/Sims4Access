"""TS4 Access Plus, merged into TS4 Access (2026-10-08).

TS4 Access Plus 0.7.1 was a separate add-on (TS4_Access_Plus.ts4script) by
Michael Maslo, contributed through LeonianUniverse: Alt-key readouts (needs,
time and work, rooms, notifications), low-need, work and bill reminders, spoken game speed and
Build/Live mode, Create and edit Sims without Create a Sim, a brand-new
family moved onto a lot, and a Build mode helper that builds rooms and whole
houses with the game's own tools. Its modules are tyjokr_a11y_plus_*.py; its
catalog bridge now lives in TooltipManager_patched.as (A11yPlusHandle).

Each module is imported on its own so one failure cannot stop the others or
TS4 Access. Its log is TS4_Access_Plus.log next to the mod and in the
Windows user folder. Do not also install TS4_Access_Plus.ts4script: both
would poll the same Alt keys.
"""
import tyjokr_a11y_speech as speech

MODULES = ('core', 'menu', 'needs', 'notify', 'time', 'rooms', 'sims', 'family',
           'build', 'house', 'furnish', 'decor', 'draw')
loaded = []
failed = []


def _load():
    import importlib
    for name in MODULES:
        try:
            importlib.import_module('tyjokr_a11y_plus_' + name)
            loaded.append(name)
        except Exception as ex:
            failed.append(name)
            speech.log_line('plus: {} did not load ({!r})'.format(name, ex))


_load()
