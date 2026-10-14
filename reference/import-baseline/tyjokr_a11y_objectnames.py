"""Give gameplay objects a hover tip so their names can be narrated.

The game client only sends hover-tip messages to the UI for objects that
declare a hover-tip style (gardening, crafted food, owned/heirloom items...).
Plain furniture declares none, so nothing appears and nothing can be spoken.

Two stamping paths, chosen by whether EA gave the object a tooltip component
(77% of tuned objects have one):

- WITHOUT a tooltip component: set `hover_tip` and write a recipe_name ui
  metadata entry directly, then push it. Nothing else manages these objects'
  tooltips, so the direct write is safe.
- WITH a tooltip component: the component owns the metadata lifecycle. It
  rebuilds lazily on the client's first-hover request, tracks its own
  handles, and DISABLES the hover tip whenever it ends up with no handles of
  its own (GameObject.has_ui_metadata_handles is component-forwarded, so
  handles written directly are invisible to that check and the tip dies on
  first hover; writing directly also duplicates recipe_name against the
  component's own fields on rich objects). Route the name through EA's
  external-field channel instead (update_tooltip_field): the rebuild merges
  external fields only where the component produced nothing itself, so EA's
  rich data always wins and our name only fills the gap. Never distribute a
  hover_tip style on these objects before their first-hover handshake: the
  engine then believes the tooltip already exists and never requests the
  rebuild, killing EA's own tips (assigned beds). The style for name-only
  objects is applied AFTER each rebuild by a wrap on update_object_tooltip.

Only objects with at least one player-facing interaction get a name; rugs,
curtains and other pure deco stay clean. An interaction counts if it is not
debug/cheat, is visible, allows user direction, and is not in the frozen
exclusion set of situational universals that EA tunes onto swaths of
otherwise inert objects. The set was computed by tools/affordance_census.py
over all 6,755 object tunings (game 1.126, 2026-08-01); regenerate it after
major EA patches.

PLAYER-VISIBLE: this makes a small name tooltip appear when hovering gameplay
objects that previously had none. Toggle with the `a11y.objectnames` cheat
command; the setting persists for the session.

The a11y.objectnames on/off choice persists via the settings file
(`object_names` key).
"""
import services
import sims4.commands
from indexed_manager import CallbackTypes
from objects.components import types as component_types
from objects.hovertip import TooltipFields
from protocolbuffers import UI_pb2 as ui_protocols
from sims4.localization import LocalizationHelperTuning

import tyjokr_a11y_settings as settings

_speech_mod = None


def _speech():
    global _speech_mod
    if _speech_mod is None:
        try:
            import tyjokr_a11y_speech as mod
            _speech_mod = mod
        except ImportError:
            return None
    return _speech_mod


def _log(message):
    mod = _speech()
    if mod is not None:
        mod.log_line(message)


def _speak(text):
    # Only used for command feedback, which must talk in every speech mode.
    mod = _speech()
    if mod is not None:
        mod.speak(text, explicit=True)


# Style 2 renders name (+ optional description) in the standard hover panel.
_STYLE = ui_protocols.UiObjectMetadata.HOVER_TIP_CONSUMABLE_CRAFTABLE

# Situational universals: interactions EA tunes onto broad swaths of unrelated
# objects that only apply with a special actor (ghost possession/powers, fame
# perks), a special object state (burnt/scratched replacement), or dev tooling
# (simRay). Their presence does not make an object "interactive".
_EXCLUDED_AFFORDANCES = frozenset((
    74457,    # fire_ReplaceBurntObject
    102255,   # Ghost_Possess_Repair
    102258,   # Ghost_Possess
    102433,   # Ghost_Possess_Break_Electrocution
    102774,   # Ghost_Possess_Break_Plumbing
    105971,   # simRay_Frozen_View
    106094,   # simRay_MindControlReaction_Panicked
    106095,   # simRay_MindControlReaction_Escape
    106859,   # simRay_Transform_Object
    116720,   # simRay_Transform_Object_WallObject
    121648,   # Ghost_Possess_Bonfire
    143965,   # Ghost_Possess_BubbleBlower
    163419,   # scratch_ReplaceScratchedObject
    168502,   # Ghost_Pet_Possess
    168664,   # simRay_ChangeClothes_Upgrade_CompletedDisplay
    168665,   # simRay_Clean_Upgrade_CompletedDisplay
    168666,   # simRay_Eat_Upgrade_CompletedDisplay
    168667,   # simRay_Panic_Upgrade_CompletedDisplay
    168668,   # simRay_Sit_Upgrade_CompletedDisplay
    168669,   # simRay_Sleep_Upgrade_CompletedDisplay
    168670,   # simRay_TransformObject_Upgrade_CompletedDisplay
    168671,   # simRay_TransformSim_Upgrade_CompletedDisplay
    182291,   # Ghost_Possess_Fire
    194245,   # famePerks_Influencer_OpenEnvelope
    194246,   # famePerks_Influencer_OpenPackage
    196759,   # famePerks_GoodReputation_GivingBack_DonateObject
    196854,   # famePerks_Influencer_OpenEnvelope_FromWorld
    196855,   # famePerks_Influencer_OpenPackage_FromWorld
    260638,   # simRay_Transform_Object_ScientistVenueGrassOnly
    324988,   # Ghost_Horse_Possess
    385718,   # ghostPowers_Abilities_Chaos_ProduceMaterial
    385719,   # ghostPowers_Abilities_Helpful_RemoveMaterial
    391304,   # ghostPowers_Abilities_Scary_Self_FlickerLights_Room
    391312,   # ghostPowers_Abilities_Scary_MusicalPossess
    392250,   # ghostPowers_Abilities_Scary_GhostlyBang_Terrain
    393624,   # ghostPowers_Abilities_Comfort_ImproveQuality
    393625,   # ghostPowers_Abilities_Comfort_Unspoil
    393630,   # ghostPowers_Abilities_Comfort_NurturePlantLife
    393658,   # ghostPowers_Abilities_Helpful_NoPossess_Instantly_Clean
    393662,   # ghostPowers_Abilities_Helpful_Instantly_NoPossess_Repair
    393663,   # ghostPowers_Abilities_Helpful_Instantly_Possess_Repair
    393664,   # ghostPowers_Abilities_Helpful_Instantly_Possess_Upgrade
    395021,   # ghostPowers_WellofSouls_AbilityReset
    395070,   # ghostPowers_Abilities_Helpful_RemoveMaterial_EmptyTrash
    415212,   # ghostPowers_Abilities_Helpful_RemoveMaterial_Mold
))

_enabled = bool(settings.get('object_names', True))
_registered = False
_stamped = set()


def _is_player_affordance(sa):
    """Mirrors the pie menu's own no-shift gate (not debug and not cheat),
    plus visibility/user-direction, minus the situational universals."""
    try:
        if sa.debug or sa.cheat:
            return False
        if not sa.visible:
            return False
        if not sa.allow_user_directed:
            return False
        if sa.guid64 in _EXCLUDED_AFFORDANCES:
            return False
        return True
    except AttributeError:
        return False


def _has_interactions(obj):
    """True if the object offers at least one player-facing interaction.
    super_affordances() covers both the tuned list and component-provided
    affordances; None context is safe (the behavior-affordance leg guards
    on it)."""
    try:
        for sa in obj.super_affordances():
            if _is_player_affordance(sa):
                return True
    except Exception as ex:
        _log('objectnames: affordance check failed on {}: {!r}'.format(
            getattr(obj, 'id', '?'), ex))
    return False


def _should_stamp(obj, force=False, inventory=False):
    if obj is None:
        return False
    if not force and obj.id in _stamped:
        return False
    if obj.is_sim:
        return False
    # Never override a tip the game already provides (gardening, crafted,
    # heirlooms, collectibles); those are richer than a bare name.
    if obj.hover_tip:
        return False
    if obj.definition is None:
        return False
    if inventory:
        # A visible inventory item needs a readable name even when its
        # affordances are inventory-only. Hidden storage is not a UI item.
        component = getattr(obj, 'inventoryitem_component', None)
        return (component is not None and not component.is_hidden
                and component.is_in_inventory())
    return _has_interactions(obj)


def stamp(obj, force=False, inventory=False):
    if not _should_stamp(obj, force, inventory):
        return False
    try:
        name = LocalizationHelperTuning.get_object_name(obj)
        if name is None:
            return False
        if obj.get_component(component_types.TOOLTIP_COMPONENT) is not None:
            # External-field channel: merged into the component's lazy
            # first-hover rebuild only where it produced nothing itself.
            # Do NOT touch hover_tip here: if a style reaches the client
            # before the first-hover handshake, the engine believes the
            # tooltip already exists and never requests the rebuild, so EA
            # content (assigned-bed tips) never materializes. The style for
            # name-only objects is applied post-rebuild by the
            # update_object_tooltip wrap installed below.
            obj.update_tooltip_field(TooltipFields.recipe_name, name,
                                     should_update=True)
        else:
            obj.hover_tip = _STYLE
            obj.add_ui_metadata('recipe_name', name)
            obj.update_ui_metadata()
        _stamped.add(obj.id)
        return True
    except Exception as ex:
        _log('objectnames: stamp failed on {}: {!r}'.format(
            getattr(obj, 'id', '?'), ex))
        return False


def _on_object_add(obj):
    if _enabled:
        stamp(obj)


def stamp_all(force=False):
    """Stamp everything on the lot.

    `force` re-applies to objects we stamped before whose tip has since been
    cleared (a tooltip component rebuild that came up empty disables the tip
    again if our external field was not yet in place).
    """
    count = 0
    manager = services.object_manager()
    if manager is None:
        return 0
    for obj in tuple(manager.values()):
        if stamp(obj, force):
            count += 1
    return count + stamp_inventory(force)


def stamp_inventory(force=False):
    """Use the existing lazy tooltip path for visible inventory names too."""
    manager = services.inventory_manager()
    if manager is None:
        return 0
    count = 0
    for obj in tuple(manager.values()):
        if stamp(obj, force, inventory=True):
            count += 1
    return count


def _install_inventory_hook():
    from objects.components.inventory_item import InventoryItemComponent
    original = InventoryItemComponent.on_added_to_inventory

    def a11y_on_added_to_inventory(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            if _enabled:
                stamp(self.owner, inventory=True)
        except Exception as ex:
            _log('objectnames: inventory name failed: {!r}'.format(ex))
        return result

    InventoryItemComponent.on_added_to_inventory = a11y_on_added_to_inventory


try:
    _install_inventory_hook()
except Exception as _ex:
    _log('objectnames: inventory hook install failed: {!r}'.format(_ex))


def enable(on):
    global _enabled, _registered
    _enabled = on
    manager = services.object_manager()
    if manager is None:
        return 0
    if on:
        if not _registered:
            manager.register_callback(CallbackTypes.ON_OBJECT_ADD, _on_object_add)
            _registered = True
        return stamp_all()
    if _registered:
        manager.unregister_callback(CallbackTypes.ON_OBJECT_ADD, _on_object_add)
        _registered = False
    return 0


def _install_tooltip_rebuild_hook():
    """After EA's rebuild: if it produced handles (which includes our merged
    external name) but chose no style, give it ours. EA styles always win;
    a rebuild that disabled the tip (no handles) is left disabled."""
    from objects.components.tooltip_component import TooltipComponent
    original = TooltipComponent.update_object_tooltip

    def a11y_update_object_tooltip(self):
        result = original(self)
        try:
            owner = self.owner
            if (_enabled and owner is not None and owner.id in _stamped
                    and not owner.hover_tip and self._ui_metadata_handles):
                owner.hover_tip = _STYLE
                owner.update_ui_metadata()
        except Exception as ex:
            _log('objectnames: rebuild hook failed: {!r}'.format(ex))
        return result

    TooltipComponent.update_object_tooltip = a11y_update_object_tooltip


try:
    _install_tooltip_rebuild_hook()
except Exception as _ex:
    _log('objectnames: rebuild hook install failed: {!r}'.format(_ex))


def _install_zone_hook():
    import zone
    original = zone.Zone.on_loading_screen_animation_finished

    def a11y_on_loading_screen_animation_finished(self, *args, **kwargs):
        result = original(self, *args, **kwargs)
        try:
            if _enabled:
                stamped = enable(True)
                _log('objectnames: stamped {} objects at zone load'.format(stamped))
        except Exception as ex:
            _log('objectnames: zone-load stamp failed: {!r}'.format(ex))
        return result

    zone.Zone.on_loading_screen_animation_finished = a11y_on_loading_screen_animation_finished


try:
    _install_zone_hook()
except Exception as _ex:
    _log('objectnames: zone hook install failed: {!r}'.format(_ex))


@sims4.commands.Command('a11y.objdiag', command_type=sims4.commands.CommandType.Live)
def a11y_objdiag(match: str = '', _connection=None):
    """a11y.objdiag <substring of tuning name>: log tooltip state of matching
    objects (e.g. `a11y.objdiag bedDouble`)."""
    output = sims4.commands.CheatOutput(_connection)
    if not match:
        output('a11y: usage a11y.objdiag <substring of tuning name>')
        return True
    manager = services.object_manager()
    if manager is None:
        output('a11y: no object manager')
        return True
    count = 0
    for obj in tuple(manager.values()):
        if obj.is_sim:
            continue
        cls_name = type(obj).__name__
        if match.lower() not in cls_name.lower():
            continue
        count += 1
        lines = ['objdiag: {} id={} hover_tip={!r} stamped={} interactive={}'.format(
            cls_name, obj.id, obj.hover_tip, obj.id in _stamped,
            _has_interactions(obj))]
        comp = obj.get_component(component_types.TOOLTIP_COMPONENT)
        if comp is None:
            lines.append('   no tooltip component')
        else:
            lines.append('   hovertip_requested={} handles={} external={}'.format(
                comp.hovertip_requested,
                sorted(comp._ui_metadata_handles.keys()),
                sorted(comp._external_field_to_data.keys())))
            try:
                from event_testing.resolver import SingleObjectResolver
                resolver = SingleObjectResolver(obj)
                lines.append('   tooltip_tests_pass={}'.format(
                    bool(comp.tooltip_tests.run_tests(resolver))))
                for i, tip in enumerate(comp._get_custom_tooltips()):
                    passed = bool(tip.object_tests) and bool(
                        tip.object_tests.run_tests(resolver))
                    lines.append('   custom[{}] style={!r} tests_pass={}'.format(
                        i, tip.tooltip_style, passed))
            except Exception as ex:
                lines.append('   test eval failed: {!r}'.format(ex))
        for line in lines:
            _log(line)
            output(line)
        if count >= 8:
            break
    output('a11y: objdiag matched {} object(s)'.format(count))
    return True


@sims4.commands.Command('a11y.objectnames', command_type=sims4.commands.CommandType.Live)
def a11y_objectnames(mode: str = 'on', _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    if mode.lower() in ('redo', 'force', 'refresh'):
        # Re-apply over anything that lost its tip after our first pass.
        _stamped.clear()
        again = stamp_all(force=True)
        output('a11y: re-stamped {} objects'.format(again))
        _speak('Re-stamped {} objects.'.format(again))
        return True
    if mode.lower() in ('off', 'false', '0'):
        enable(False)
        settings.set('object_names', False)
        output('a11y: object hover names OFF (restart or reload lot to clear existing tips)')
        _speak('Object hover names off.')
        return True
    stamped = enable(True)
    settings.set('object_names', True)
    output('a11y: object hover names ON ({} objects stamped)'.format(stamped))
    # Report how many objects the game currently believes carry a hover tip,
    # which is what actually drives the tooltip appearing at all.
    tipped = 0
    total = 0
    try:
        manager = services.object_manager()
        if manager is not None:
            for obj in tuple(manager.values()):
                if obj.is_sim:
                    continue
                total += 1
                if obj.hover_tip:
                    tipped += 1
    except Exception as ex:
        _log('objectnames: audit failed {!r}'.format(ex))
    output('a11y: {}/{} objects currently have a hover tip'.format(tipped, total))
    _log('objectnames: audit {}/{} objects have hover_tip'.format(tipped, total))
    _speak('Object hover names on. {} objects.'.format(stamped))
    return True
