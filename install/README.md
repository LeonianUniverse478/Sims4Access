# What goes in your Mods folder

All four files are here. Copy them into
`Documents/Electronic Arts/The Sims 4/Mods/`:

    Sims4Access.ts4script
    a11yscan_names.bin
    a11yscan_objects.bin
    prism.dll

If you are upgrading from before the rename, delete
`a11yscan_Companion.ts4script` first, or the game loads both copies.

## About the two .bin tables

They are lookup tables built from The Sims 4's own string and object resources:
definition id to catalog name, and string key to text. Object Definitions carry
no display name at runtime, so without these the buy catalog reads out as
"object" several thousand times.

They are built from the game's data, and they are included here so the mod
works out of the box. **Rebuilding them yourself is still worth doing**, and
takes a couple of minutes:

    python toolsebuild_tables.py <output dir>
    py37\python.exe tools\package.py

`rebuild_tables.py` reads your game packages *and your Mods folder*, so your own
content mods get real names. A table built on someone else's install knows
nothing about the mods you have, and knows about packs you may not own.

## prism.dll

Someone else's project, under a different licence. See `PRISM-NOTICE.md`.
