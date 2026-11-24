# Unified house workflow and basement verification

- Add one Build my house entry covering original presets, square/rectangular front/back or four-room layouts, and the original room-list planner. Common review supports aligned stories, optional basement, individual room types/names and actual compass positions. Preserve native room/door geometry and the construction workers.
- Refresh the native Lot floor-range cache before Build-mode room scans; marshal worker scans through the simulation pump. This prevents cached floor-zero bounds from hiding a new basement or story.
- Reconfirm Basement Tool after camera preparation; log native floor bounds and funds after drawing. Replace the misleading generic wrong-size message for a failed basement step.

Code: Scripts/tyjokr_a11y_house_workflow.py; targeted updates in Scripts/tyjokr_a11y_basement.py; final bootstrap hook in contrib-reference/modules/tyjokr_a11y_contrib.py. Controls in CONTROLS.txt. Focused tests in tools/test_house_workflow.py and tools/test_basement_adapter.py.
