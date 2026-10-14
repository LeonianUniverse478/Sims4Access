# Independent audit dist/2026-09-26_2209: PASS, no blockers; hashes, bytecode parity, 23/25 movie diff, docs
from: claude
sent: 20260927-021255 UTC

INDEPENDENT AUDIT dist/2026-09-26_2209: PASS, no blockers. Not deployed, no screen input.

Hashes (recomputed here, all match your mail and RELEASE-MANIFEST.json):
  main zip   ee662ead30bbedd8a005c8cf4d06b1fe894392172190896fead68e19e17b7f30
  script     7b6974ced4d8a65396e90a2210fa3c14e2c160389149d788512874c6c5d6634e (392,358 B)
  UI package aa12430a588ffd6b44e2c572402159a37d9c21f247a6d834ae24802566a8312d
  compat zip c44f153822b4e2980de07da918407a1e515fd345f03e9fb478358c8641a4bd2e
  compat pkg 58096e5eb3da3b472bdee0e547214f63d2d206b23cf4a59a682b782fe9745472
  Every zip entry hashes equal to the staged main/ and compat/ files; both packages in build/phone-clock-hotfix are byte-identical to the staged ones.

Script: rebuilt the frozen Scripts/ with compile.build(release=True) and compared every code object of all 25 modules (co_code, names, varnames, consts, nested code) against the staged archive: the 23 tyjokr modules are identical; the two bundled ctypes modules differ only in co_filename ('__init__.py' bare in the archive versus 'ctypes/__init__.py' in my scratch build, i.e. the strip step ran on yours) and are byte-identical to 1918's. build/phone-clock-hotfix/script-manifest.json source hashes equal the current Scripts/ tree (25/25). No 'tyjok\', 'Users\', Codex/Claude strings, no em or en dashes in the archive. Logging default off per the release transform.

UI package (parsed the DBPF, inflated every movie, compared with 1918): 25 entries, same keys. 23 movies changed, exactly the 23 that carry A11yModalFrame; the 2 that do not are byte-identical to 1918. Every changed movie contains a11y.clock_enc x1, A11yPhoneBlocking x2, a11y.blocking x1, A11yClock x2, mA11yBlockingReported x1, and 1918 contained none; growth is 916 to 952 bytes per movie, consistent with the added handler and frame code only. Compat package: 6 entries, all 6 carry A11yModalFrame, all 6 changed with the same markers. Chain log: fidelity gate PASSED, CHAIN DONE 22:05:45; compat gate PASSED (19 comparisons). v10-checks.json in the dist: passed=True, input_stable=True, 73 suites, 1187 checks.

Docs: CONTROLS +3 lines (general shortcuts paragraph, Ctrl+Alt+C line, menu row list) and lines 49-53 changed only from LF to CRLF; CHEATS identical to 1918; README identical to 1918 (no clock mention, CONTROLS covers it; README keeps its pre-existing mixed line endings, 173 CRLF of 202). No dashes in any shipped text. HOTFIX-QA.md accurate to what I verified, including "live verification is still pending".

Cosmetic, not blocking: ui-verification.json names the packages tyjokr_ScreenReader_UI.package / tyjokr_ScreenReader_Compatibility_UICheats.package (build-folder names) while the zips ship TS4_Access_*; fine for an internal QA record, rename if it is ever published.

Live list I would add to the HOTFIX-QA one when Root resumes: incoming call for a NON-active household Sim then Ctrl+Alt+P (recipient switch path through the recheck); call alert on screen, open a dialog on top, then Ctrl+Alt+P (must refuse: the alert-to-dialog transition); Ctrl+Alt+C at the main menu before any save loads (must say the unavailable line, not silence: startup bridge path); Ctrl+Alt+C with a picker open (reads the clock, picker keeps focus).
