# Announce serving details in the object scanner

Food entries report the remaining servings and the quality shown in the game's hover tip. The client resolves the quality heading and tier labels in the player's language. A description supplied by the game, such as the spoiled label, takes precedence over the tier. The scanner strips display markup and omits unavailable quality text while retaining the serving count.

When a localized catalog name contains all three Polish quantity variants, the scanner reads the standalone name. Other localization requests keep their original text.

The scanner tree tests cover serving counts, quality tiers, tooltip overrides before and after a mouse hover, missing translations and quantity variants. To verify in game, scan a fresh platter before hovering over it, compare the spoken quality with its hover tip, then take a serving and scan again. Compare a spoiled platter and scan an ordinary object. In Polish, also check a dish whose catalog entry contains several grammatical forms.
