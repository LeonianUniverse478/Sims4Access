# Passing work between Leo and tyjokr

## ZIP workflow (ready to use)

Each source kit is a named snapshot. `.handoff/baseline.json` identifies that snapshot with hashes; `.handoff/baseline.zip` preserves its editable sources. Both people keep the same original kit. Leo edits his copy and runs `Dev.ps1 return --summary "..." --tests "..."`. The resulting small ZIP contains:

- `RETURN.json`: starting snapshot ID and before/after hashes for each changed file.
- `CHANGES.patch`: a readable unified diff, including additions and deletions.
- `files/`: complete replacement sources for changed/added files.
- `SUMMARY.md`: his explanation and testing report.

Generated binaries, GFX baselines, private local configuration, and `.handoff` are not returned. If the baseline inputs need changes, coordinate a new kit instead of sneaking binary replacements into a source return.

The reviewer runs `Dev.ps1 review <zip>` in a copy with the original `.handoff`. Review rejects another baseline, path traversal, Windows device/alternate-stream paths, duplicate entries, oversized payloads, unexpected files, and damaged hashes. It regenerates the diff from trusted baseline bytes; it does not trust the sender's patch. It writes a separate review folder and never executes returned code or merges it.

`clean` means the local file still matches the baseline or already matches the return. It does not mean the change is correct. `CONFLICT` means the local file also diverged: inspect both changes before combining them. For deletions, review the manifest; do not assume absent files should be deleted automatically.

After tyjokr approves changes, his assistant applies only approved edits/deletions, then runs the relevant tests and build. Keep a backup of the prior source. The next round should start from a new source kit/checkpoint created by the maintainer, so both people share the newly accepted baseline. Never rerun a checkpoint in Leo's changed folder before sending a return: doing so would erase the comparison base.

When integrating into the original maintainer workspace, the kit's root `CLAUDE.md` maps to `docs/development/kit/CLAUDE.md`, the template used for future kits. Do not put Leo-specific assistant instructions at the maintainer project's root. Inside a source-kit copy, it stays at the root.

If Leo sends a second return before receiving a new kit, it is cumulative against the same baseline. Already-applied identical changes are clean; unrelated concurrent edits still get flagged. Label the second return clearly so the reviewer does not apply an older ZIP afterward.

## Preparing the next handoff

After accepting source changes, the maintainer builds and reviews the new paired candidate. From that source tree, assemble a fresh kit with the reviewed `dist` directory:

```powershell
py -3.7 tools/make_source_kit.py --baseline "dist/<reviewed timestamp>" --game "D:\Games\The Sims 4" --ffdec "D:\ffdec\ffdec.jar"
```

Substitute the real local paths. Assembly checks the candidate's frozen Python sources and Flash snapshot, copies the reviewed UI pair, and creates a new baseline in a new output folder. Keep the original return, review report, previous kit and new kit together outside Mods. Give Leo the new source ZIP before the next round; do not replace his `.handoff` in place while he has unreturned edits.

A new game/UI Cheats patch needs the rebase process too. Simply generating a fresh manifest around old game movies does not make them compatible with a new patch. Update the version/provenance records and rerun the full build checks before calling that a reviewed baseline.

## Keeping evidence

Put concise test notes and reproducible steps in `docs/development/changes/<short-name>.md` before returning. That source file is included automatically. Include only relevant, redacted log excerpts. The `--tests` text is a contributor report, not an independently verified pass. Reviewers should rerun tests after applying approved changes.

Send compiled test ZIPs separately only when someone needs to reproduce that exact binary. Always send the source return too, and identify which source snapshot produced the binary. Never develop by unpacking and decompiling each other's ts4script.

## Optional private Git workflow

If both people want a hosted workflow later, a private repository with one branch per change and pull requests provides persistent history and inline review. Do not publish the current kit wholesale: it includes private development baselines and third-party/game inputs. Keep generated output, personal configuration, extracted game movies, speech binaries, and local baselines out of the source repository; arrange baseline assets separately.

Git is not required for this handoff, and no repository/account or public upload has been created. Git branches or local Git bundles can be added later without changing the Python/GFX build process. Avoid using a shared synchronized working folder as version control: a build must see one consistent source snapshot.
