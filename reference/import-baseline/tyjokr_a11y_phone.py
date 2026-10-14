"""Announce waiting household calls; open the recipient's existing phone UI.

No automatic responses, timeout changes or background-thread game calls.
"""
import functools
import sims4.commands
import tyjokr_a11y_settings as settings
import tyjokr_a11y_speech as speech

_waiting = []  # (dialog_id, owner_id), oldest first


def _recipient(dialog):
    owner = getattr(dialog, 'owner', None)
    info = getattr(owner, 'sim_info', owner)
    return getattr(info, 'sim_id', 0), info


def _note(dialog, phone_ring_type):
    from ui.ui_dialog import PhoneRingType
    import services
    if phone_ring_type == PhoneRingType.NO_RING or not settings.get('keyboard', True):
        return
    owner_id, info = _recipient(dialog)
    if not owner_id:
        return
    client = services.client_manager().get_first_client()
    if client is None or info not in client.selectable_sims:
        return
    token = (dialog.dialog_id, owner_id)
    if token in _waiting:
        return
    _waiting.append(token)
    del _waiting[:-32]
    name = ' '.join(part for part in (getattr(info, 'first_name', ''),
                                      getattr(info, 'last_name', '')) if part)
    speech.speak('Phone for {}. Control Alt P opens the waiting call or text.'.format(name),
                 source='event')


def open_waiting():
    """Runs only on the simulation pump or a game command callback."""
    import services
    import distributor.ops
    import distributor.system
    service = services.ui_dialog_service()
    client = services.client_manager().get_first_client()
    if service is None or client is None:
        return False
    active = getattr(service, '_active_dialogs', {})
    while _waiting:
        dialog_id, owner_id = _waiting[0]
        dialog = active.get(dialog_id)
        info = services.sim_info_manager().get(owner_id)
        if dialog is None or info not in client.selectable_sims:
            _waiting.pop(0)
            continue
        if client.active_sim_info is not info and not client.set_active_sim_by_id(owner_id):
            speech.speak('The recipient is not available.', explicit=True)
            return False
        # Flash waits for ActiveSimId to match before clicking the phone.
        op = distributor.ops.SendUIMessage('A11y|phone|{}'.format(owner_id))
        distributor.system.Distributor.instance().add_op_with_no_owner(op)
        return True
    speech.speak('No waiting call or text.', explicit=True)
    return False


@sims4.commands.Command('a11y.phone', command_type=sims4.commands.CommandType.Live)
def a11y_phone(_connection=None):
    return open_waiting()


def _install():
    from ui.ui_dialog_service import UiDialogService
    original = UiDialogService.dialog_show
    if getattr(original, '_a11y_phone_hook', False):
        return

    @functools.wraps(original)
    def dialog_show(self, dialog, phone_ring_type, *args, **kwargs):
        result = original(self, dialog, phone_ring_type, *args, **kwargs)
        try:
            if not self.is_phone_silenced and dialog.dialog_id in self._active_dialogs:
                _note(dialog, phone_ring_type)
        except Exception as ex:
            speech.log_line('phone: announcement failed: {!r}'.format(ex))
        return result

    dialog_show._a11y_phone_hook = True
    UiDialogService.dialog_show = dialog_show


try:
    _install()
except Exception as ex:
    speech.log_line('phone: hook unavailable: {!r}'.format(ex))
