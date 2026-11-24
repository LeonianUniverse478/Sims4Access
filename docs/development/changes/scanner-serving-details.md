# Announce serving counts and native object quality in the scanner

An object with a servings counter reports its remaining servings. Independently,
the scanner reads the quality row of the selected object's native hover tip.
This includes drinks, individual servings, garden plants, fish and other
objects when the game shows quality for them. Rarity and sale value are
separate fields. An ordinary object with no quality data needs no extra
round trip. These details apply when reading a selected object in the world.

On the simulation thread, the scanner asks the selected object to prepare
its metadata just as it would for its first hover. On the client it uses
GetObjectMetadata and the game's localisation keys, including descriptions
with tokens. The regular and gardening panels have different quality rules;
for example, a dead plant can show its former quality. Skill restrictions
are respected. The reply is scoped to one row announcement and one 64-bit
object ID. A missing or late reply cannot replace a newer selection.

When a localized catalog name contains all three Polish quantity variants, the scanner reads the standalone name. Other localization requests keep their original text.

For an in-game check, scan a platter before hovering over it, take a serving
and compare the platter and the single plate with their respective tooltips.
Also compare a mixed drink, a fish with a freshness description, a plant
and an ordinary object with no quality row. Move quickly between two objects
of different quality and check that only the current row speaks. In Polish,
also check a dish whose catalog entry contains several grammatical forms.

Rebased onto the 18 November dev build. Item announcements retain the new
native dirty/dusty suffix alongside servings and quality, and the grouped
scanner's selection and preview behaviour remain unchanged. Offline checks
cover that combination as well as stale replies and native tooltip rules.
