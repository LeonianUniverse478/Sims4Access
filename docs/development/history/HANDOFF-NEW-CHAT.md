> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Handoff for a new Claude chat: Screen Reader v14 work with Codex

Written 2026-09-25 08:45 EDT. Read this first, then the top section of
HANDOFF-SCANNER-INTEGRATION.md and the tail of COLLAB-CLAUDE-CODEX.md.

## 1. What this is

Claude and Codex work together on the Screen Reader mod (workspace folder
`My Script Mods/ScreenNarrator-integration`, installed in
`<user-home>\Documents\Electronic Arts\The Sims 4\Mods\tyjokr_ScreenReader`).
The user is often away from the PC and has authorized both agents to launch and
drive the game for unsaved live tests, never both at once. Communication is a
file mailbox (section 3). The user's direction, relayed through Codex, still in
force: keyboard-on simplified travel whenever traveling (Sim menu, phone, M key,
vacation), family-first labels with resident names, finish the Build actions
window, keep going until the listed work is complete, do not stall waiting.

## 2. Standing rules (never break)

- Never copy anything into Mods while TS4_x64.exe runs (`tasklist | findstr TS4_x64` must be empty).
- Deploys only after the other agent's approval: send `deploy request: ...`
  with exact sha256 hashes, wait for `re: deploy request ... APPROVED`.
  Codex has done every install so far with `tools/deploy_reviewed_v14*_pair.py`
  (hash checks before and after, unique backup under build/codex-deployed-before-*).
- One `mailbox/GAME-LOCK` file names who may drive the game. Codex holds it now.
  Never drive the game window while the user is at the PC (a physical Escape
  stops Codex's automation; treat that as the user being present).
- Unsaved game sessions only. No public upload. No em or en dashes in any copy.
- README.txt is the user's own wording; Codex maintains it from drafts
  (Claude's draft: build/claude-proposals/README-build-draft.txt).
- TEST docs never claim a live pass without log evidence or a capture named in
  the Evidence column ("no live pass claimed" on frozen candidates).
- Ownership: Codex owns the shared Flash template `flash/TooltipManager_patched.as`
  unless it explicitly hands a patch to Claude, plus live testing, README, and
  its tools (`tools/test_*review*`, `audit_frozen_ui.py`, `freeze_script_candidate.py`,
  deploy helpers). Claude owns all Python under `Scripts/`,
  `flash/extra-classes/ControlPanel.as`, the pipeline tables, docs listed below,
  and usually runs the UI chain (Codex has run it when Claude was slow to reply;
  never run two chains at once).

## 3. The mailbox (how to talk to Codex)

Folder: `mailbox/`. Two maildir boxes: `to-claude/` (Codex writes, Claude reads)
and `to-codex/` (Claude writes, Codex reads). Each message is one .md file,
written atomically by `send.py`; the reader moves it from `new/` to `cur/`.
Nothing is deleted. Full protocol: `mailbox/README.md`.

Send to Codex (run from the project folder):

```bash
python mailbox/send.py to-codex "short subject" -m "one line body"
```

```bash
python mailbox/send.py to-codex "short subject" -f path/to/body.md
```

Read everything Codex sent (marks it read; if you piped the output through
`tail` and lost text, re-read the files in `mailbox/to-claude/cur/`):

```bash
python mailbox/inbox.py
```

Be woken by new mail: arm the watcher with the Monitor tool on
`bash "<project>/mailbox/watch_claude.sh"` with the maximum 30 minute timeout,
and re-arm it every time it expires. Known limitation: when several messages
land inside one minute the Monitor sometimes delivers only the first event, so
on every wake run `python mailbox/inbox.py` and also glance at `ls mailbox/to-claude/new`.
Codex reads with `python mailbox/wait.py to-codex` (blocking). If my sent files
stay in `mailbox/to-codex/new/`, Codex has not read them yet.

Conventions: one topic per message; reply subjects start with `re:`; put
evidence paths and exact hashes in the body; the long record goes to
COLLAB-CLAUDE-CODEX.md (append-only, timestamped sections).

## 4. Where things stand (08:45 EDT)

Installed pair (v14i): script `39e792019564cb854e8b64b635e50c2fbb3e0ba4b081b1e3abd3ab6c88139275`
(build/v14h-build-script-candidate, Python unchanged since) and UI package
`d302876933c2d6aadc57a85db7b8e540a3678a15d9b92822fe67b1ba7a1be977`
(build/v14i-resync-ui-candidate). cfg untouched. Backups under
build/codex-deployed-before-v14g, -v14h, -v14i.

Live PASS (see TEST-V14.md rows): keyboard travel list end to end (worlds,
places, family-first labels with residents, master and secondary units, arrival
with companions, Back rows, cancel, map fallback with arrival, keyboard off,
travel list off); vacation rental through the list with charge and arrival (row
25, one EA teardown assertion noted as EA's own race); affordability refusal
(27); solo M key travel (28 partial); rental panel quote narration (31);
catalog product restored after the Build actions window (row 32 partial).

Live FAIL, open: after leaving Build mode (F1) or an explicit cursor off, physical
mouse clicks still act at the last virtual cursor point, later at nothing (row
35). v14g added SetMouseInputEnabled(true), v14i added SetVirtualCursorPosition(-1,-1)
on disable; neither fixed it. Findings from the Olympus PCode
(flash/work-1.128.90/pcode/ea_ClassLibraryOlympus): the native virtual cursor is
the gamepad emulated mouse; EA enables it only in controller mode inside a
NavManager cursor adapter; mode switching is engine-owned
(CallGameService "ToggleControllerAndMouseKeyboard", engine answers with
ControllerModeToggled which sets SystemUtils.UsingController). Nothing in EA
enables it in mouse-keyboard mode, which is what the Build cursor does.

Agreed next step: Codex's diagnostic build (v14j). Codex applied
A11yBuildSnapshot instrumentation to the template (05:50, native return values,
caught errors, SystemUtils flags, mouse coordinates); Claude approved it with
three additions (statement terminator after `var disabledResult = ...`, an
enable-after snapshot, log arrivals of UsingControllerToggled and
CursorModeToggled). Experiment order: A) if UsingController flips because of our
enable, send ToggleControllerAndMouseKeyboard on disable; B) restraint parity on
disable; C) if neither, redesign the Build cursor as a foreground-guarded Windows
pointer instead of the native virtual cursor. Codex has been silent since 05:50
with Claude's 05:50 and 05:53 messages unread; the game process from its v14i
session is still open under its lock.

Also held: the Ctrl+Alt+H hub chord in Build mode with the catalog open only
speaks the dialog help (keys._chord treats the catalog scope as a modal; H is the
`help` intent). Fix, if the trace confirms, is client-side (Flash distinguishes
catalog scope from a true modal), not a Python bypass. Still unproven live:
actual object placement with undo and redo, M refusals (row 29), price bridge
rows 30 and 33 to 34 on the current pair.

## 5. Build and freeze routine (Claude's part)

Script candidate:

```bash
rm -rf build/<tag>-script-candidate && py -3.7 tools/build_script_archive.py build/<tag>-script-candidate && py -3.7 tools/run_checks_v10.py > build/<tag>-run-checks.log && py -3.7 tools/freeze_script_candidate.py build/<tag>-script-candidate
```

UI chain (rebuild all movies, PCode fidelity gate, package, compat; about 10
minutes; its log is exclusively locked while it runs, watch
`flash/work-1.128.90/gfx/patched_*.swf` timestamps for progress):

```bash
powershell -ExecutionPolicy Bypass -File flash/chain.ps1 -Tag <tag> -Work work-1.128.90
```

Then `py -3.7 tools/freeze_ui_candidate.py <tag>` (needs a passed
build/v10-checks.json whose template hash matches) and
`py -3.7 tools/audit_frozen_ui.py build/<tag>-ui-candidate` (Codex's read-only
audit, safe to run). Send both hashes to Codex; Codex audits and installs after
mutual approval. FFDec rules for Flash edits: no `++`, write `x = x + 1`; the
template is CRLF; a Python `write_text` normalizes line endings (harmless, but
say so in the diff mail).

Tests live in `tools/test_*.py` (py -3.7) and `tools/test_*.js` (node); all
are picked up by run_checks_v10 (556 checks at the last run). Patch scripts
that touch Python with triple quotes are written as files first, not typed into
a Bash heredoc.

## 6. Files to read for detail

- HANDOFF-SCANNER-INTEGRATION.md (top sections, newest first) and
  COLLAB-CLAUDE-CODEX.md (append-only history, newest at the bottom).
- TEST-V14.md (rows 1 to 35 with evidence) and Codex's TEST-V14-COMPLETION.md.
- build/claude-proposals/: v14-travel-list.diff (Python vs the v13b base),
  v14g-build-exit.diff, v14i-cursor-resync.diff,
  a11y-build-product-preserve.as (integrated by Codex), README-build-draft.txt,
  codex-cursor-diagnostic-plan.md.
- Memory file screen_reader_travel_dialog_completion.md (in the Claude memory
  folder) for the technical gotchas: dialog completion from Python, price
  bridge, M handshake, modal cancels the held catalog product, virtual cursor
  ownership, chord hook timing.
