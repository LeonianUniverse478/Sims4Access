# Businesses window and plus/minus amounts (2026-10-04)

Leo asked for the transfer labels to extend to businesses, including mod businesses such as the strip club.

## Survey

- WickedWhims' strip club registers a business type into EA's `BusinessTuning.BUSINESS_TYPE_TO_BUSINESS_DATA_MAP`. It runs a BusinessManager subclass (StripClubManager) and uses EA's FundsTransferDialog, RetailSummaryDialog, BucksPerk and business employee types.
- NisaK Wicked Perversions builds on WickedWhims' strip club.
- Its own menus (open hours, points, dances, price markup) are WickedWhims pickers, which the mod menu census covers.
- So EA's business screens and system serve the stores and the strip club alike.

EA's owned-business panel (HouseholdInfoVenuePanel, Retail/FinancesContent) labels its figures with separate text fields and tooltip holders. It has a markup dropdown with no text label, and signs and colours its amounts. The RetailSummary line items use KeysGP RETAIL_SUMMARY_POSITIVE_FUNDS ("+  {0.Money}") and NEGATIVE_FUNDS ("-  {0.Money}") with a colour stylesheet.

## Behavior

- **Businesses row** (new module tyjokr_a11y_business.py), in the accessibility menu after Events:
  - For every business the household owns (`business_service().get_business_managers_for_household`), it reads from the BusinessManager.
  - The figures are the ones EA sends to the panel in `construct_business_message`: open or closed, `get_star_rating()`, business `funds.money`, `daily_items_sold`, the customer manager's `session_customers_served`, `daily_revenue`, `get_daily_outgoing_costs(include_employee_wages=False)`, `get_daily_net_profit(include_employee_wages=False)` and `markup_multiplier` (spoken as a percent).
  - It also reads `employee_count`, `get_total_employee_wages_per_hour()` and `meets_minimum_employee_requirment()`.
  - The name is the zone's name from the persistence service. Enter opens EA's panel (OpenHouseholdInfoVenuePanel). One unreadable business is logged and skipped.
- **Plus and minus:** narrator `_clean_glyphs` says "plus" and "minus" for a sign standing before a simoleon amount ("-  §500" is spoken as "minus 500 simoleons"), because screen readers often skip a lone dash. Hyphenated words are untouched.

## Files

- New: Scripts/tyjokr_a11y_business.py and tools/test_business.py (6 tests).
- Changed: Scripts/tyjokr_a11y_hub.py (the Businesses row; the pack-rows line split back onto two lines), Scripts/tyjokr_a11y_narrator.py, Scripts/tyjokr_a11y_lang.py, CONTROLS.txt and docs/patreon/03.
- Test update: tools/test_simology.py's row-order check now follows Businesses.

## Not yet done

- Labels inside EA's business panel itself (the markup dropdown name and figure labels), the perks panel and employee management. These wait for a live check of what is silent.
- No business has been opened in game with this build.
