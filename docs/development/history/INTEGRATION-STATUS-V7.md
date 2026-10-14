> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# Accessibility scope and glaroc integration

September 15 live-test update: V9.6 is verified, installed and tested in-game.
TEST-V9-6.md consolidates the current results
and remaining tests. FEEDBACK-V8.md preserves the player's reports. Calls/texts
remain untested, and main-menu/CAS speech remains incomplete.

Reviewed against the September 7 a11yscan source and the available 1.127.41
EA Python/Flash references. Historical comparison documents contain broader
coverage claims than the evidence supports. This table is the current scope.

| Feature | Current position |
|---|---|
| Nearby Sims/objects, categories, distance, bearing and real interaction pies | Integrated. V9.3/V9.4 bound repeated work and idle refresh. Live test: 82 entries in 12 categories, mean 7.83 ms over 12 scans; idle after 30 seconds. The active Sim is included. |
| Scanner visual | Existing optional narration captions; `a11y.captions on`. The diagnostic picker is not the scanner's normal display. |
| Keyboard dialog responses, purchase/Sim/event pickers, Age Up and trait reassignment | V6 plus V7 navigation fixes. Keyboard-only runtime acceptance remains necessary. Shared pickers are not each a separate missing movie patch. |
| Panel focus, camera guards, Escape, text-field escape, informative Profile entries | Live tests establish panel entry/close, world Escape, text-field entry/Tab exit, hidden Simology reveal and Build/Live ownership release. Player previously passed Profile traversal. Physical held-camera behavior remains unverified. |
| Calendar | Relative dates/events, Busy Sim names, one weather header, filters, hidden holiday traditions and individual Stay Over guests passed targeted live checks. V9.6 duration/time dropdowns activate, focus their selected value and close with Escape back to the field. |
| Needs, mood, moodlets, wants/fears, aspirations | Existing localized UI and hover narration remain primary. Whole need targets passed for ordinary and vampire Sims, including Sebastian's Vampire Energy and Thirst. Ashton's completed school/aspiration tasks and incomplete aspiration progress were correctly narrated. Broader variants remain untested. |
| Current action and funds | Added to the accessibility menu. Action uses EA's localized interaction name; funds use the household's actual balance. |
| Household Sim selection | Added with selectable-household membership rechecked at activation. This switches the controlled Sim, not the household or save. |
| Incoming phone/text | Recipient announcement and keyboard entry added. Selects the correct household Sim only on request. Does not answer automatically or extend expiry. |
| Self/phone/inventory/contact entry points | Active-Sim interaction menu, waiting phone and existing Inventory/Relationships panels reachable from the hub. Separate remote-contact and inventory scanner categories are not integrated. |
| Server-side dialog fallback | Not integrated. It must preserve native client closure, selected ids, multi-select constraints and dialog-specific reply data. A generic yes/no response is not sufficient. |
| Map-free travel, Go Home, household moves/merge | Not integrated. Must retain normal availability and transition validation and close the client map correctly. |
| Careers and event planning | School requirements, performance tooltip, completed grade task and homework were separately reachable. Existing game panels/pickers receive keyboard improvements. Separate server-side career/event workflows are not integrated. |
| Read-only tile grid | Not integrated. Useful next step toward home setup, independently of placement. |
| Build catalog placement/undo | Placement/undo not integrated. Catalog focus, spatial movement, reveal and native tooltips were exercised. Glaroc's placement still needs footprint, rotation, routing, funds and undo validation before adoption. |
| CAS bypass, Stories and appearance wizard | Not integrated. Sim creation from a lot is distinct from creating the first Sim at startup. No CAS movie override is added. |
| Save and main-menu load shortcuts | Glaroc's scratch-save and resume-slot-copy shortcuts are not adopted. The normal native save flow still needs an accessible entry and end-to-end validation. |
| Main menu | Unresolved after live startup probes. Gamedata, native UI input and Python core ticks run, but PostServerCommand/Distributor do not bridge startup; native commands with 0/NO_CONTEXT did not reach UI and a fixed localhost URLLoader request failed. All probe files are removed from Mods. |
| Gamepad | Existing work remains incomplete; this pass focuses on keyboard accessibility. |
| Developer hot reload | Not integrated. Secondary to gameplay access; thread/alarm retirement must be reliable. |
| First-install settings popup | Still deferred at the user's request. Settings remain manually accessible. |

## Kept constraints

The normal package retains the original 23 movies plus AgeUpPanel, with six
UI Cheats compatibility movies. ClassLibraryGamedata was established as the
live shared TooltipManager copy in earlier in-game testing. The 135-definer
inventory does not justify overriding 135 movies. EngagementLibrary and
every CAS movie remain excluded.

The release sibling is untouched. Existing mouse-hover narration and native
localized text remain the primary speech path. New English/Polish hub labels
are mod vocabulary; other languages currently fall back to English for those
new labels. Existing translated vocabulary is retained.

## Remaining priorities

1. Test physical held keys, fast scanner chords, NVDA/Polish and an actual
   incoming call. V9.6 dropdown and V9.5 reverse-Tab checks passed. Very short
   full Ctrl+Alt chords can still be missed between polls.
2. Find a supported startup transport before claiming accessible load/new-game
   or independent CAS. Rebuilding more movies does not address the observed
   missing UI/Python delivery.
3. Broaden inventory and picker coverage; the formerly silent inventory
   cellphone now speaks its localized name while richer earbud tips remain
   intact. Polish generic restored Add labels, duplicate school targets,
   stray school summary text and the hub's image placeholders/help text.
4. Add a read-only grid, validated travel flows and remote contact access.
5. Build Sim creation/home placement workflows with reversible operations
   and normal game validation. These are required for an independent first
   playthrough; V7 does not yet provide that full experience.
