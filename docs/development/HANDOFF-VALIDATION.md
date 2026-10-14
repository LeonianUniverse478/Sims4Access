# Source-kit validation, September 27, 2026

This validates the developer handoff and build process. It does not certify new gameplay behavior. All 25 runtime Python modules remain identical to the reviewed September 26, 22:09 candidate. That candidate's phone and clock live checks remain pending.

## Builds

- Built a source-only copy in a separate folder with spaces in its path, using its own local tool configuration and bundled dependencies.
- Both `Dev.ps1 build --scripts-only` and the full `Dev.ps1 build` completed and staged matching script/UI test ZIPs. The helper executable was compiled from source before its smoke tests.
- The full build regenerated all 25 main movies and all 6 UI Cheats compatibility movies. Both fidelity gates passed. Package resource bytes, class-definition sets and non-code GFX tags were checked.
- All 29 canonical Flash source/recipe files included in the kit matched the copy used for that full build. Two obsolete deploy/rebuild scripts in the original maintainer tree were intentionally excluded.
- Both rebuilt UI packages were byte-for-byte equal to the reviewed reference packages:

| Package | SHA256 |
| --- | --- |
| Main UI | `aa12430a588ffd6b44e2c572402159a37d9c21f247a6d834ae24802566a8312d` |
| UI Cheats compatibility | `58096e5eb3da3b472bdee0e547214f63d2d206b23cf4a59a682b782fe9745472` |

The current offline suite passed 1,208 checks across 75 isolated suites, with both `passed` and `input_stable` true. Counts include repeated imported checks; they are not a count of unique gameplay scenarios. The new exchange and assembly tools contribute 21 regression tests.

## Handoff and rejection tests

- A real PowerShell `return`/`review` round trip retained a summary containing spaces, handled a source file without a final newline, included an added document and flagged a conflicting local edit. Review left the local edit untouched.
- Unit tests covered added/changed/deleted files, invalid paths and Windows aliases, malformed archives, hash mismatches, wrong baselines, unexpected files, local conflicts, final-newline markers and case-variant aliases.
- A deliberately changed UI template caused the scripts-only build to stop before tests or packaging; its build lock was released.
- Assembly checks the full runtime source set, candidate Flash snapshot, original EA movie bytes against the installed game, and reference package hashes.
- Claude independently tested a second-generation kit assembled from inside a first-generation kit. It needed no original workspace dependencies. Added runtime source and modified extra ActionScript classes were correctly rejected against the old reviewed candidate.
- Personal paths are redacted from documentation before hashing. Code is not silently rewritten: a detected private path there stops assembly. Tests cover escaped, ordinary and MSYS profile paths, generic OneDrive guidance, UTF-8 BOM preservation and contradictory reuse evidence.

## Limits

No game was launched or controlled for this handoff, and no build was installed into Mods or published. The kit is pinned to the recorded game/UI Cheats inputs and FFDec toolchain. Its successful rebuild is evidence of reproducibility, not a guarantee against every possible runtime crash. Each new feature still needs focused in-game testing and review.
