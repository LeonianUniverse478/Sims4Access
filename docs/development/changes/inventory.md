# Store a scanned object in an inventory

The Live mode scanner can move the selected object to the active Sim's inventory
(Ctrl+Backspace) or the household inventory (Shift+Backspace). This gives
keyboard users a way to put away an object without dragging it. The first press
reads the object's name. Repeat the same shortcut within 15 seconds to confirm.

On the simulation thread, household storage checks ownership and placement
flags on the home lot before calling `build_buy.move_object_to_household_inventory`
with no failure flags. It verifies the object ID in the household inventory.
Personal storage uses `inventory_component.can_add` and `player_try_add_object`,
including for urns, and checks membership afterwards.

Offline tests cover both destinations, a change of destination, an occupied
object, unavailable simulation input and keyboard ownership while editing.
Shortcut help has an extra row for these two commands. For a live check, try
both shortcuts on an eligible object, change selection before confirming,
and check that the object appears in the intended inventory only once.
