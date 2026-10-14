> Historical evidence. Commands, paths, counts and defaults below may be obsolete. Read START-HERE.md first.

# ScreenNarrator-integration: provenance and rules

Cloned 2026-09-03 22:13 from `My Script Mods/ScreenNarrator/` for the
a11yscan (glaroc) feature integration. See `A11YSCAN-REVIEW.md` for the
review and adopt list.

## What this tree is

The 2026-08-28 RELEASE state of Screen Reader:

- Sources are byte-identical to `_rc-frozen-2026-08-20/` (tools/rc_verify.sh
  on the parent reported only the two .package artifacts as changed, which
  is the 2026-08-28 rebuild for game 1.127.41 plus the 6-movie UI Cheats
  v1.59.1 compat).
- `dist/tyjokr_ScreenReader_2026-08-28.zip` was cut from these sources. Its
  ts4script matches the tree copy module for module except
  `tyjokr_a11y_speech.pyc`, where compile.py --release flips the
  `log_enabled` default (expected). Its UI package is byte-identical to
  `tyjokr_ScreenReader_UI.package` here.
- NO gamepad / console-nav code. That experiment (v7-v18) lives only in
  `ScreenNarrator/_wip-gamepad-2026-08-27/` and is defunct for now. The
  only `UsingController` strings in this tree are EA's own code inside the
  exported extra-classes.

## What was left out of the clone

`_cas-probe`, `_rc-frozen-2026-08-20`, `_removed-from-mods-2026-08-26`,
`_wip-gamepad-2026-08-27`, `dist/`, every `__pycache__`, all `flash/*.log`,
the stray `flash/patched_TimeControls.swf`, and the work dirs
`flash/work-1.126.78`, `flash/work-1.127.41-compat`, `flash/work-uic159`.
`flash/work-1.127.41/gfx/` was recreated with ONLY the 23 `ea_*.swf`
originals plus SOURCE.txt; `patched_*`, `pcode/`, `ttm_*.as` regenerate.

## Rules for work in this tree

1. `py -3.7 compile.py` DEPLOYS `tyjokr_ScreenReader.ts4script` into the
   live Mods folder. Do not compile until a build is meant to be tested.
2. Flash rebuilds: `flash\rebuild_all.ps1 -WorkDir <this tree>\flash\work-1.127.41`
   then `python flash\build_ui_package.py <same WorkDir> [output path]`.
   Always give an explicit output path for experimental packages.
3. Never run two flash pipelines at once; gate with gate_pcode.py and
   check for PASSED before any deploy.
4. The parent `ScreenNarrator/` tree stays the release tree. Nothing is
   merged back until the user says so.
5. No string tables (STBL/OBJD) and no invented language where the game
   already has the words (user directive 2026-09-03).

## Work done in this tree

- 2026-09-03: scanner v1 (glaroc's world scanner rebuilt on our plumbing).
  Change list, build artifacts and the in-game test plan: SCANNER-TEST.md.
  Build outputs live in `build/` (ts4script) and the UI package path given
  to build_ui_package.py; the copies of the release artifacts hashed below
  are untouched.

## Hashes at clone time (SHA-256)

```
7fc2350dfa6729b81b528f0f11559e80517be088c169871b072b916cd996c901 *Scripts/tyjokr_a11y_keys.py
a54040e16459ea1d65173bb6a8d33d5ddb154be905bb8294a5c93b7ccd1dc135 *Scripts/tyjokr_a11y_lang.py
b708db13ada0d10c183e3ed5ffcd87b69c15bc3e9fe258a054138112a35ae8c6 *Scripts/tyjokr_a11y_narrator.py
57703e7d9663d5e387140bb66b8f6c2378bb06645139d492c5a79d0eb56e3843 *Scripts/tyjokr_a11y_objectnames.py
aa0509c32cfc583622471443ddf17bf874d269152310021d1caa7ecb287ebc2b *Scripts/tyjokr_a11y_settings.py
8fa791cc76ef4a400ec19e4ad2c2e993831a1a26c4e9f1a74bdbb6218fa6caaf *Scripts/tyjokr_a11y_speech.py
540ab53aa5f465e58a5e8176716a3cbf0ecc89d6401508356da4912706181a54 *compile.py
b07e7861c8e683f5fc2b1ada1dd84c57560fb410f68679345762ec79df8ca7f6 *flash/TooltipManager_patched.as
27cc7cdc2e5bc83f8a69ecb206fff9ecad978c890f795b609698e70e3da4e3e6 *flash/extra-classes/CASCustomizerMain.as
e111104552b2e694c5fae747f59afc541ad250be73b88778fef899c9a8160618 *flash/extra-classes/CatalogImageCellView.as
d6b2712ecf82cb643f10fd75c1eb1590f034b7470527c3f4a8c8fd5fb1f90f38 *flash/extra-classes/CommodityContainer.as
28af875917f8ddeffaab8aa54315bab8b928b4982b6f5ab4d6088bb0d362560b *flash/extra-classes/DialogMain.as
1b18eb0de3b1464d9054fca0b5dd2363a12107e8b02f6315de14c8800c0639f0 *flash/extra-classes/HoverTip.as
763d5549bd99be34cd1891b4227fb3a5532215af412f9879790d4e028548b46b *flash/extra-classes/InteractionButton.as
688696ebc1b7dd30659aeffc3e28fac4b721c68529d0ab4dcf9f71fa0376fe63 *flash/extra-classes/MoodContainer.as
5960cd0ac69799d6ccec021d501766a0e6d034df6c58e826bc33aea25d922348 *flash/extra-classes/NotificationsMain.as
f937634f53cc348637563e82400eaec4686c1da40ba7ac3c695be71d10f14f59 *flash/extra-classes/PhoneCategoryScreen.as
7c081ecf411b3fd9fe9245e85092b2d70fcee4e81808797856bc34e6e64e1ac3 *flash/extra-classes/PickersMain.as
e9737ad7aba11227475013f01515ecb09a236650c9dafc403731176e597fe8ba *flash/extra-classes/PickersPurchaseMain.as
527031ad137c1b50cdb49ddaccfae31779b14723dc01b0fad57e2b93ca8db6ab *flash/extra-classes/PieMenuMain.as
48f1e24d99edc9e5d799a67e1005a36d37486b34da2fb6203624d8f095f0969e *flash/extra-classes/PurchasePickerCellView.as
9567380becba38409d92fa730a4a704aff8a45d455eb1b8b023e113300d087e1 *flash/extra-classes/SimHeadline.as
99805326e5c1f263608d529fd2f1f27d90ac0fbb0647ae8e1f495de8905f5e29 *flash/extra-classes/TimeControlsMain.as
2710802d5b4ab02764848823a9f86fb3cde841af1d90d85d0ead037a1be9a255 *flash/rebuild_all.ps1
8e3aeb6e036b6e34ce71630bccbee879f4f48d8ca5f3032502482372b0a54eb4 *flash/build_ui_package.py
b5a7a7123f8f42673bfe9e3b10500ad6d66cfb6b6e5360e456e955ab3d7b3892 *tyjokr_ScreenReader.ts4script
36854ed2a6dc96382efacf61a9a2dc4a55a9482a66994b961b8478d069c687f8 *tyjokr_ScreenReader_UI.package
7244f59cf938cbd3b05c98e2c5411165b3f450e58cbc57896fa2772d43698c85 *tyjokr_ScreenReader_Compatibility_UICheats.package
```
