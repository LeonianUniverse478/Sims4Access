"""Open the selected running event's native goal HUD, without acting on goals."""
import time
import threading

_serial = 0
_pending = None
_registered = False


def _log(message):
    import tyjokr_a11y_speech as speech
    speech.log_line('event goals: '+message)


def _unavailable():
    import tyjokr_a11y_lang as lang
    import tyjokr_a11y_speech as speech
    speech.speak(lang.t('event goals unavailable'),explicit=True)


def _expire(serial):
    global _pending
    if _pending is None or _pending['serial']!=serial: return
    job=_pending
    _pending=None
    import services
    if int(services.current_zone_id())!=job['zone']:return
    _log('native UI query timed out')
    _unavailable()


def receive(text=''):
    global _pending
    import services
    import tyjokr_a11y_narrator as narrator
    try:
        parts=narrator._decode_percent(text).split('|')
        if len(parts)!=3 or _pending is None:return False
        job=_pending
        if parts[0]!=str(job['serial']) or parts[1]!=str(job['zone']):return False
        if int(services.current_zone_id())!=job['zone']:return False
        _pending=None
        if time.monotonic()>job['until']:return False
        _log('native HUD status={} event={}'.format(parts[2],job['event']))
        if parts[2]!='opened':_unavailable()
        return parts[2]=='opened'
    except Exception as exc:
        _log('invalid native reply: '+str(exc));return False


def _register():
    global _registered
    if _registered:return
    import sims4.commands
    @sims4.commands.Command('a11y.eventgoals_enc',command_type=sims4.commands.CommandType.Live)
    def command(text: str='',_connection=None):return receive(text)
    _registered=True


def open_goals(situation_id):
    global _serial,_pending
    import services
    import tyjokr_a11y_hub as hub
    import tyjokr_a11y_pump as pump
    manager,situation=hub._event(situation_id)
    if situation is None:return False
    _register()
    _serial+=1
    job={'serial':_serial,'zone':int(services.current_zone_id()),'event':int(situation_id),'until':time.monotonic()+4.0}
    _pending=job
    hub._ui('A11y|eventgoals|{}|{}|{}'.format(job['event'],job['zone'],job['serial']))
    # The timer never touches game data; only the simulation pump may expire it.
    timer=threading.Timer(4.1,lambda:pump.post(_expire,job['serial']))
    timer.daemon=True;timer.start()
    return True


def _open_in_zone(situation_id, zone):
    """A picker selection must still belong to the lot where it was opened."""
    import services
    if int(services.current_zone_id()) != zone:
        return False
    return open_goals(situation_id)


def open_current(zone):
    """Shortcut entry: open the sole event, or explicitly choose between events."""
    import services
    import tyjokr_a11y_hub as hub
    import tyjokr_a11y_keys as keys
    try:
        # This command runs on the simulation thread. Recheck ownership and the
        # lot after Flash's key guard, before opening a native picker.
        zone = int(zone)
        if (int(services.current_zone_id()) != zone or not keys._enabled or keys._editing_active
                or keys.blocking_active()):
            return False
        events = [event for event in hub._events()
                  if getattr(event, 'display_name', None) is not None]
        if not events:
            hub._say('no events')
            return False
        if len(events) == 1:
            return _open_in_zone(events[0].id, zone)
        rows = [(event.display_name, hub.menu._raw(hub._event_detail(event)),
                 lambda value=event.id: _open_in_zone(value, zone))
                for event in events]
        return hub._window('current event goals', 'event goals selection instructions', rows)
    except Exception as exc:
        _log('shortcut unavailable: ' + str(exc))
        _unavailable()
        return False
