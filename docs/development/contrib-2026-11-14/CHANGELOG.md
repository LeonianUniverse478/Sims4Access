# Cumulative contribution changelog — 14 November 2026

This test build combines upstream adb868c (12 November, game 1.129.39.1030) with the later contribution work below. It includes standard TS4 Access and the matching UI Cheats 1.59.1 compatibility package.

## Earlier contribution, now integrated upstream

Scanner distance/scope selection, furniture movement, wall-side and height support, room labels, placement layers, and experimental bare-ground/water/ceiling/fence placement are retained through the upstream implementation. Duplicate local adapters and their old polling/settings bootstrap have been retired. Remaining local extensions start once through the simulation-thread queue.

## Build-grid targeting and furniture placement

- Repeated number-row 1 presses cycle through supporting furniture and its attached contents separately, so a television can be selected independently of its stand.
- Catalog placement uses the explicitly focused supporting surface. The same surface and a compatible free native slot are rechecked before registration and payment; full or incompatible surfaces refuse purchase.
- Add experimental native snapping for dining chairs to dining tables and desk chairs to desks. Face an adjacent compatible table/desk or focus it with 1, then press Enter. Native slots supply the seat position and rotation.
- Recheck the exact selected seat after the game releases its placement tool, and verify attachment before charging. A changed, occupied or invalid seat cancels the transaction.
- Add independent settings for chair snapping and chair-to-table orientation hints; avoid duplicate hints when snapping already describes the target.
- Preserve custom room labels ahead of inferred room names, with inferred names available through a passive room-name bridge.

## House building, roofs and lot orientation

- Combine the house presets and configurable stacked-house planner into one Build my house workflow, with square/rectangular layouts, room arrangements, aligned stories, room names/types and a plan review.
- Add detached small-structure planning for sheds, garages, party houses and enclosed winter gardens, with footprint, layout, entrance side and naming choices.
- Add an optional lot-planning description layer to the existing grid: detected buildings, rooms, pools, exterior flooring, landscaping, occupied ground and apparently clear outdoor ground.
- Add building names and descriptions of detected footprints, floors, rooms, doors and windows; add room/build descriptions and door connections.
- Add a roof assistant with flat-deck, gabled and hipped choices, detected building/room footprints and overhang presets. Flat mode describes the existing top-floor ceiling as the deck; it does not create a pitched roof piece.
- Add roof-level descriptions, a chimney placement assistant and read-only stair-shape diagnostics.
- Add an experimental basement adapter using the native Basement Tool, with room-result checks and its own setting and diagnostics.
- Verify floor changes against native current/minimum/maximum floor data. Refresh cached lot floor ranges so new stories and basements are visible to room scans.
- Isolate stair transitions to the active house plan and clear them when the plan ends, preventing failed plans from affecting later builds.

## Resolution, scaling and build input

- Replace the fixed/divided-screen coordinate assumption with measured native UI projection, live game-client dimensions, window origin and scoped Windows DPI conversion.
- Check focus, native Build/dialog state, geometry changes and actual pointer arrival before helper clicks/drags. Abort on resize or focus changes and release helper-owned mouse/modifier state.
- Add read-only display and build-coordinate diagnostics, including a11y.buildcoords, to record the measurements used for placement.

## UI navigation and announcements

- Port accessibility hooks onto the current 25 supported game UI movies and matching UI Cheats movies, retaining shared handlers and native controls.
- Needs: use native trait-dependent need names, including occult variants, and omit invalid percentages. Skip empty temperament/curse cells.
- Needs, Simology and Aspirations: traverse instantiated controls instead of repeatedly restarting one-cell section wrappers; omit linked decorative highlight artwork from focus stops.
- Expose visible occult rank/points rows and individual ability controls to keyboard navigation.
- Purchase pickers: keep focus on the item when confirmation is unavailable, announce native cart/funds reasons, and expose quantity controls. Preserve UI Cheats cart behavior.
- Book-title/description dialogs: traverse row wrappers to the actual text inputs and existing confirmation footer.
- Game Options: activate the native checkbox, dropdown or button inside each row; announce visible labels, values, descriptions and settled checkbox state. Improve Graphics option labels.
- Social Bunny: expose visible post/contact actions, including message, friendship and reaction buttons, with author/post context.
- Photography: add Photography controls to focus an already open camera and announce selected native filters.
- Wedding planning: announce the native selected state of venue rows after activation.
- Expose visible child actions inside clubs, Gallery subscription cards, rental-property cards and household cards.
- Manage Worlds: expose neighborhood expansion, destination-household controls and native apartment-map unit selection. Traverse rental region/building wrappers and individual unit cards.
- Main-menu scenarios: traverse groups/cards and native Play controls; announce rendered descriptions, difficulty, requirements, roles and goals through the existing startup speech transport.
- Running events: add Current event goals under the selected event, focusing the native goal HUD; discard stale event/zone scopes.

## Cleaning and household access

- Add dirty and dusty scanner suffixes from current native object states, without changing scanner categories, ordering or refresh behavior.
- Add read-only cleaning diagnostics to inspect native object states when a mess has an unhelpful name.
- Add Floor actions here to open the native floor interaction menu at the active Sim's current position and floor, exposing available floor/vacuum actions.
- Add native Away actions for eligible household Sims who are elsewhere, using the game's existing portrait action picker.

## Speech helper lifetime

- Own the Windows fallback PowerShell child with a native kill-on-close Job Object, so it terminates when its parent exits or crashes, including during stalled PowerShell startup.
- Serialize startup and reuse the live child; restart closes ownership, waits for termination and closes stdin. Ownership/launch failure cleans up the candidate.
- Keep pipe writes outside the lifecycle lock so a blocked write cannot prevent cleanup. Register normal-exit cleanup where available; kernel ownership also covers abrupt termination.
- Bound the separate optional setup-helper PowerShell startup check to five seconds, with an explicit skip when unavailable; actual helper test failures remain failures.

## Validation

The latest run has 131 passing suites, zero failed suites and one optional setup-helper suite skipped; source inputs remained stable. Ten speech-lifecycle tests include real Windows normal-parent-exit and forced-parent-termination checks, plus blocked-pipe cleanup. All 43 existing speech-mode checks also passed against the compiled script. UI fidelity evidence accompanies the retained matching UI build. Added or repaired game UI/build flows still require in-game testing; this changelog records implemented behavior, not a claim that every flow has been confirmed live.
