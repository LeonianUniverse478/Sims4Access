"""Native answers and refusal reasons shared by the simplified flows.

A picker is only ever answered through EA's dialog service: the pick goes
through the dialog's own pick_results (row membership) and the answer
through respond, so EA's listener runs as if the player had clicked. The
selection limits are checked first. Nothing here sets picker attributes or
turns on the service's automatic answering. A refused interaction reports
the game's own reason: the client fills the text of a native notification,
which the notification narration reads.
"""
import tyjokr_a11y_lang as lang
import tyjokr_a11y_speech as speech


def _service():
    import services
    return services.ui_dialog_service()


def dialog_active(dialog):
    """True while EA still holds this exact dialog as active."""
    try:
        service = _service()
        lookup = getattr(service, 'get_dialog', None)
        if lookup is not None:
            return lookup(dialog.dialog_id) is dialog
        return service._active_dialogs.get(dialog.dialog_id) is dialog
    except Exception:
        return False


def answer_picker(dialog, picked_results):
    """Answer an open EA picker with these row option ids and OK. False
    when the dialog is gone, the count is outside its limits, or EA refuses
    the pick or the answer. Nothing is changed when the dialog is gone, the
    count is outside the limits or EA refuses the pick; when EA accepts the
    pick but refuses OK, the dialog stays open holding that pick."""
    picked = list(picked_results)
    if not dialog_active(dialog):
        speech.log_line('native: dialog {} is gone; nothing answered'.format(getattr(dialog, 'dialog_id', '?')))
        return False
    minimum = getattr(dialog, 'min_selectable', 0) or 0
    # EA's max_selectable is a policy object (get_max_selectable); only a
    # plain number is checked here.
    maximum = getattr(dialog, 'max_selectable', None)
    if not isinstance(maximum, int) or isinstance(maximum, bool):
        maximum = None
    if len(picked) < minimum or (maximum is not None and maximum > 0 and len(picked) > maximum):
        speech.log_line('native: {} picked is outside dialog {} limits ({} to {})'.format(
            len(picked), dialog.dialog_id, minimum, maximum))
        return False
    try:
        from ui.ui_dialog import ButtonType
        service = _service()
        if not service.dialog_pick_result(dialog.dialog_id, picked_results=picked):
            speech.log_line('native: dialog {} refused the pick {}'.format(dialog.dialog_id, picked))
            return False
        if not service.dialog_respond(dialog.dialog_id, ButtonType.DIALOG_RESPONSE_OK):
            speech.log_line('native: dialog {} refused OK'.format(dialog.dialog_id))
            return False
        return True
    except Exception as ex:
        speech.log_line('native: answering dialog {} failed ({!r})'.format(dialog.dialog_id, ex))
        return False


def show_reason(tooltip, sim):
    """EA's own reason text (a localized string factory) as a native
    notification. True when shown."""
    if tooltip is None or sim is None:
        return False
    try:
        from ui.ui_dialog_notification import UiDialogNotification
        notification = UiDialogNotification.TunableFactory().default(
            sim, text=lambda *_, **__: tooltip(sim))
        notification.show_dialog()
        return True
    except Exception as ex:
        speech.log_line('native: reason unavailable ({!r})'.format(ex))
        return False


def say_refusal(result, sim):
    """A refused push: the spoken line first, then the game's reason when
    its test gives one."""
    speech.speak(lang.t('action unavailable'), explicit=True)
    tooltip = getattr(getattr(result, 'test_result', None), 'tooltip', None)
    if show_reason(tooltip, sim):
        speech.log_line('native: refusal reason shown')
        return True
    return False
