# TS4 Access Plus - notification history (Alt+L). Keeps the last 30 pop-up notifications
# (promotions, bills, invitations, skill gains...) so they can be read again later.
import tyjokr_a11y_plus_core as core

_history = []     # newest last: (clock text, title proto or None, text proto or None)
MAX = 30


def _copy(ls):
    try:
        from protocolbuffers.Localization_pb2 import LocalizedString
        out = LocalizedString()
        out.CopyFrom(ls)
        return out
    except Exception:
        return None


def _record(dialog_msg):
    title = _copy(dialog_msg.title) if dialog_msg.HasField("title") else None
    text = _copy(dialog_msg.text) if dialog_msg.HasField("text") else None
    if title is None and text is None:
        return
    when = ""
    try:
        import services
        import tyjokr_a11y_plus_time as t
        now = services.time_service().sim_now
        when = "{} {}".format(t.day_text(now), t.clock_text(now))
    except Exception:
        pass
    _history.append((when, title, text))
    del _history[:-MAX]
    core.log("notification recorded ({} kept)".format(len(_history)))


def _install():
    from ui.ui_dialog_notification import UiDialogNotification
    original = UiDialogNotification.distribute_dialog

    def a11yplus_distribute_dialog(self, dialog_type, dialog_msg, **kwargs):
        try:
            _record(dialog_msg)
        except Exception:
            core.log_exc("record notification")
        return original(self, dialog_type, dialog_msg, **kwargs)

    UiDialogNotification.distribute_dialog = a11yplus_distribute_dialog


try:
    _install()
except Exception:
    core.log_exc("install notification hook")


@core.hotkey(ord("L"), "last notifications")
def open_history():
    if not _history:
        core.speak("No notifications yet since the game was loaded.")
        return
    rows = []
    for (n, (when, title, text)) in enumerate(reversed(_history)):
        label = text if text is not None else title
        desc = title if (text is not None and title is not None) else None
        rows.append((label, desc if desc is not None else "Received {}".format(when), n))
    core.choose("Notifications", "Newest first. {} kept.".format(len(_history)), rows, lambda v: None, tag="notify")
