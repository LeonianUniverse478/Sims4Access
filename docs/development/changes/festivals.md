# Festivals menu and travel (2026-11-25)

Leo: there is no way to get to a festival. The game's only route is the festival flyer (DynamicSignDialog). The calendar's Read flyer button or a festival sign opens it, and its Travel button can't be reached by keyboard.

## What it does

- **Ctrl+Alt+A, or Accessibility menu, Places, Festivals:** lists every scheduled and running festival, running ones first, each with when it's on (from the scheduler) and the game's own time text.
- **Enter on a festival:** opens its menu.
  - The first row is Travel. If the Sim can't go, it says why, for the same reasons the flyer disables its button: not started yet, already on the festival street, or on vacation.
  - Then When, Where (the festival lot's name) and each advertised activity with its description.
- **Travel:** does what the flyer's button does: `drama.travel_to_event_zone`, which for a festival is `travel_to_destination`. It pushes the festival's travel interaction on the active Sim, with a terrain pick of the festival lot, and says whether the game took it.
- **Read flyer:** `FestivalDramaNode.show_festival_info` is wrapped. A festival on the calendar opens this menu instead of the flyer. A festival that isn't on the calendar keeps the game's flyer.
- **Console command:** `a11y.festivals`.

## Sources

All checked against the 1.129.39 game files:

- `drama_scheduler/festival_drama_node.py`;
- `drama_scheduler/drama_node.py`;
- `server_commands/drama_commands.py`;
- the Calendar movie's `ScheduleFestivalEntry`;
- the DynamicSignDialog movie's `SignContent.OnConfirmClick`.

## Not covered yet

What happens at the festival itself:

- Light and Dark team scores (`lamp_festival`);
- contest results (`logic_festival` and the festival contest drama nodes);
- finding stalls on the open street.

These need a live visit first.

## Checks

`tools/test_festivals.py`: 9 tests. Not tested in game.
