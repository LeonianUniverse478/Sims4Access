"""Known contacts through EA's relationship-portrait interaction path.

Contacts do not need instantiated Sims or a position on the loaded lot.
The native client requests, displays and resolves its own interaction menu.
"""
import sims4.commands
import tyjokr_a11y_lang as lang
import tyjokr_a11y_menu as menu
import tyjokr_a11y_speech as speech


def _contacts(actor):
    tracker = actor.sim_info.relationship_tracker
    seen = {actor.sim_info.sim_id}
    result = []
    for info in tracker.get_target_sim_infos():
        if info is None or info.sim_id in seen or tracker.is_hidden(info.sim_id):
            continue
        seen.add(info.sim_id)
        name = ' '.join(part for part in (info.first_name, info.last_name) if part)
        if name:
            result.append((name, info.sim_id))
    return sorted(result, key=lambda item: (item[0].casefold(), item[1]))


def open_contact(sim_id, actor_id):
    import services
    import tyjokr_a11y_scanner as scanner
    from server.pick_info import PickType
    actor = services.get_active_sim()
    if actor is None or actor.sim_info.sim_id != actor_id:
        speech.speak(lang.t('contact changed'), explicit=True)
        return False
    names = {ident: name for name, ident in _contacts(actor)}
    if sim_id not in names:
        speech.speak(lang.t('sim unavailable'), explicit=True)
        return False
    # PICK_PORTRAIT is EA's relationship-panel path. It supplies the remote
    # target as picked_item_ids and retains all native availability tests.
    # A world PICK_SIM would wrongly require an instantiated target.
    pos = actor.position
    name = names[sim_id].replace('|', ' ')
    return scanner._send_ui('A11y|pick|{}|{}|{}|{}|{:.3f}|{:.3f}|{:.3f}|{}'.format(
        sim_id, int(PickType.PICK_PORTRAIT), int(services.active_lot().lot_id),
        name, float(pos.x), float(pos.y), float(pos.z), int(actor.level)))


def open_contacts():
    import services
    import tyjokr_a11y_hub as hub
    actor = services.get_active_sim()
    if actor is None:
        speech.speak(lang.t('load a household first'), explicit=True)
        return False
    actor_id = actor.sim_info.sim_id
    rows = [(menu._raw(name), None,
             lambda ident=ident: open_contact(ident, actor_id))
            for name, ident in _contacts(actor)]
    if not rows:
        speech.speak(lang.t('no contacts'), explicit=True)
        return False
    return hub._window('known contacts', 'contacts instructions', rows)


@sims4.commands.Command('a11y.contacts', command_type=sims4.commands.CommandType.Live)
def a11y_contacts(_connection=None):
    return open_contacts()
