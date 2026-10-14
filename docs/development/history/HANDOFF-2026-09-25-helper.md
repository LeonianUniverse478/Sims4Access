> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Screen Reader handoff — September 25, 2026, evening

## Current stopping point

The pre-launch helper is finished as a **test build**, delivered to the user, and independently approved by Claude. The user wants to ask questions next. Do not resume build-mode development or live testing automatically.

Project root:
`<original-project>`

## What is ready

- **Helper:** `dist/ScreenReader-Enable-Mods-and-Play-v1-test.zip`
  - SHA256: `3d2c4e414f4af8f2659408cff13401da9548ecacd1e83f4cbf74188497daf117`
  - Extract into Mods, then open `ScreenReaderHelper/Enable Mods and Play.cmd`.
  - Enables `modsdisabled=0` and `scriptmodsenabled=1` in Options.ini; preserves other contents and encoding, backs up originals, refuses changes while the game is running.
  - Native Windows controls, keyboard shortcuts, version notices, Enable Only and Enable and Play actions.
  - Does **not** modify GameVersion.txt or bypass EA's first-launch reset after an update. If EA resets settings, exit and run the helper again.
  - Exactly five packaged files: CMD, frontend PS1, Core PS1, compatibility.json, README.txt. No EXE or DLL.
  - 912 checks across 55 suites passed with stable inputs (`build/v10-checks.json`), including 54 helper checks. Claude also ran all 54 against the extracted ZIP and approved it in `mailbox/to-codex/new/20260926-005221-claude-approved-helper-zip-3d2c4e41-for-tester-handoff.md` (locate by subject if moved).
- **Latest mod download:** `dist/ScreenReader-v14u-Prism-Scanner-test-build.zip`.
  - SHA256: `423676e12a7c04ec350e7469cf6e37bd22208522b2c8af93d6f9ed2e987a833f`
  - Prism migration, scanner filtering by active Sim, performance cleanup, fresh-config Sim action narration on and speech rate 3 are included.
  - Last known local installation is still **v14t**, not v14u. Recheck before deploying; preserve the user's existing settings byte-for-byte.

## What remains

1. Helper tester validation: NVDA reading, keyboard navigation, and actual game launching. UI construction and file operations were tested; real settings and game launches were not exercised during helper development.
2. Collect tester feedback on Prism/NVDA and scanner behavior. Automated passes are not live accessibility sign-off.
3. Build-mode accessibility remains unfinished and paused behind the higher-priority Prism/scanner/helper work.
4. A source-only voice-reset fix in `Scripts/tyjokr_a11y_narrator.py` now uses `settings.DEFAULTS` for rate/volume/voice. It is **not in v14u**; include and review it when preparing the next mod build.
5. Helper follow-ups, non-blocking: clearer missing-Options.ini status (`OptionsFound`), optional backup pruning. Experimental `helper/ScreenReaderHelper.exe`, `.cs`, and `tools/build_prelaunch_helper.ps1` remain in the working tree but are deliberately excluded from distribution.

## Development cautions

- Keep the frozen mod ZIP separate from helper work. Do not package the whole helper directory blindly; use the five-file allowlist above.
- Invisible UI testing was diagnosed by Claude: Codex sandbox processes can run on a separate desktop; Hidden startup can also hide the first window. Frontend now explicitly calls ShowWindow in Shown. This was not evidence that the ordinary CMD launcher failed.
- Three old test processes were left running at last inspection: PIDs 31840, 44812 (PowerShell fixture UI), 28292 (experimental native helper). Verify current process identity before any cleanup; never kill a reused PID blindly.
- An earlier approval request failed because the automatic review service returned an authentication error. It did not execute. No outstanding approval is needed to use the delivered ZIP.

## Communicating with Claude

Claude is a separate live collaborator using the filesystem mailbox, **not** a Codex subagent. Run these commands from the project root:

```powershell
py -3.7 mailbox/send.py to-claude "Short subject" -m "Message with findings and the specific request."
py -3.7 mailbox/send.py to-claude "Long review request" -f "path/to/message.md"
py -3.7 mailbox/wait.py to-codex 30
```

Alternatively inspect `mailbox/to-codex/new/*.md`, ordered by time. Move messages you have read into `mailbox/to-codex/cur/`; some older messages remain in new, so timestamps matter. Claude's watcher normally picks up outgoing messages automatically. Do not edit watcher markers or write directly into new; use send.py for atomic delivery.

Send concrete paths, hashes, test evidence, and explicit ownership of edits. Claude authored `tools/test_prelaunch_helper.ps1` and its Python wrapper; Codex authored the helper. Coordinate before overlapping edits. Before installing anything into Mods, send a `deploy request` with exact hashes and game-closed evidence, then wait for Claude's matching approval. See `mailbox/README.md`; longer shared history is in `COLLAB-CLAUDE-CODEX.md`.

Useful checks:
```powershell
py -3.7 tools/test_prelaunch_helper.py
py -3.7 tools/run_checks_v10.py
```

Run the full suite only against stable source. Keep user-facing updates concise and distinguish packaged, locally installed, and live-tested states.
