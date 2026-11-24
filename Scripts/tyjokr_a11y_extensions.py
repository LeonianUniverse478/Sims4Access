"""Load only local extensions not integrated into upstream TS4 Access."""
import tyjokr_a11y_speech as speech

_installed = False

def install():
    global _installed
    if _installed:
        return
    _installed = True
    # Scanner ranges, moving furniture, room labels, wall/surface placement
    # and layer keys now belong to upstream's native modules and key loop.
    import importlib
    for name, explicit in (
        ('tyjokr_a11y_chair_alignment', False),
        ('tyjokr_a11y_roof_tools', False),
        ('tyjokr_a11y_house_planner', False),
        ('tyjokr_a11y_lot_grid', False),
        ('tyjokr_a11y_detached', False),
        ('tyjokr_a11y_build_coordinates', True),
        ('tyjokr_a11y_build_helpers', True),
        ('tyjokr_a11y_basement', True),
        ('tyjokr_a11y_house_workflow', True),
    ):
        try:
            module = importlib.import_module(name)
            if explicit:
                module.install()
        except Exception as exc:
            speech.log_line('local extension {} failed: {!r}'.format(name, exc))
    speech.log_line('local extensions installed on upstream-native contributions')

