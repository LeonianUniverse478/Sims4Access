# What goes in your Mods folder

Four files:

    Sims4Access.ts4script
    a11yscan_names.bin
    a11yscan_objects.bin
    prism.dll

`prism.dll` is here. The other three are **not in this repository**, on purpose.

`a11yscan_names.bin` and `a11yscan_objects.bin` are built from The Sims 4's own
string and object tables, and the `.ts4script` embeds a copy of them. Those
strings are EA's, not ours, so this project does not redistribute them. Build
them yourself from your own installed game — it takes a couple of minutes:

    python tools\rebuild_tables.py <output dir>
    py37\python.exe tools\package.py

`rebuild_tables.py` reads your game packages *and your Mods folder*, so content
mods get real names too — a table built on someone else's install would be
wrong for yours anyway.

Prebuilt copies may be attached to a GitHub Release. That is a judgement call
for whoever publishes the release, not something the source tree should carry.
