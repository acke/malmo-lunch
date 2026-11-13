# malmo-lunch

Claude Code plugin: pick lunch in Malmö.

## Contract

- Skill `lunch` (`skills/lunch/SKILL.md`) runs `lunch.py list`, prints its output verbatim (the script owns the whole format: one scrollable list, most-visited group first, then one group per area, continuous numbering, ends with the question), and records the user's pick with `go`. No `AskUserQuestion` (4-option cap). Everything is fetched live on each run; no restaurant list or menu is cached or hard-coded outside `standing.json`.
- Sources (server-rendered HTML, `robots.txt` allows both, no official API, stdlib-only Python 3):
  - `https://www.menydags.se/lunch/malmo`, paginated `?sida=N`. Primary list, has area labels.
  - `https://www.mylunch.se/vastr-hamnen/` and `/malmo/`. Adds places menydags lacks (e.g. Välfärden, Orkanen) and today's real dish rows. Merged by normalized name; if it fails, menydags alone is used.
  - `skills/lunch/standing.json`: places outside the aggregators (Pink Head and Aro Deli in Malmö Centrum; Holy Greens and Clemens in Malmö Saluhall, Hamnen; P2 on Dockplatsen, Orkanen and Locali on Nordenskiöldsgatan, all Hamnen). Dishes come from a scraped `menu` page (`nordrest`: today's weekday block of the current-week buffet on nordrest.se, wins over the garbled mylunch row for Orkanen; `p2`: today's weekday block of Green/Local/World Wide dishes on restaurangp2.se; `clemens`: today's Veckans Lunchmeny block on clemenskott.se; `holygreens`: first 5 dishes on holygreens.se/meny, chain-wide) or a hand-kept `dishes` list (Locali: poké bowl names from localifood.se, no daily lunch; Aro Deli: focaccia names from the menu PDF linked on arodeli.se, no daily lunch; Pink Head: its menu loads client-side from weiq.app behind credentials, so the list is hand-kept from its own Lunch menu, veg variants collapsed; it ages, refresh it by reading weiq.app/pinkhead1/meny in a browser). `fixed: true` = no daily lunch, regular menu; such rows get `standing: true`. `note` is shown only when no dishes are found.
- lunchmap.se is not usable: dishes render client-side and `/api/` is disallowed.
- `lunch.py list [--area NAME]` → the finished text list (see above); `--json` prints the raw rows instead, as a JSON list `{slug, name, area, dishes[{name,desc,price}], summary, visits, fav, standing?}`. `fav` = one of the 5 most-visited places (by `visits`), listed first in visit order; then the rest by name. Fetch failure prints `ERROR: ...` and exits non-zero; no places prints a one-line notice. Restaurants with no menu today are dropped, as are areas too far from the office (Hyllie, Limhamn, Möllevången).
- Same place on several sources is merged by a normalized name (drops words like restaurang, kvartersrestaurang, brasserie, hotel, malmö, 1912). `summary` is up to 6 dish names with ingredient lists cut (`med ...`, comma lists), taken from whichever of the teaser / dish rows names more dishes. Source noise is filtered: section labels, "Serveras ..." and English translation rows, allergen codes, à-la-carte rows with a price, weekday prefixes.
- `standing.json` wins over scraped rows of the same name. Always show dish names, never meta notes like "menu unreliable": La Fonderie, Ruths and Saltimporten show their scraped dishes.
- `lunch.py go NAME` records a visit; `lunch.py undo NAME` removes one. Favorites are learned from visits, never set by hand. The skill calls `go` after the user picks a place.
- Prefs: `$XDG_CONFIG_HOME/malmo-lunch/prefs.json` (default `~/.config/malmo-lunch/prefs.json`), `{"visits": {normalized-name: count}}`. Keyed by the same normalized name used for merging sources, so counts survive a place moving between sources. One file per user; nothing shared.
- Network: `www.menydags.se`, `www.mylunch.se`, `holygreens.se`, `www.clemenskott.se`, `restaurangp2.se`, `www.nordrest.se`.

## Rules

- Don't add other sources/caches unless menydags breaks; if the HTML changes, fix the regexes in `lunch.py`.
- "Gäller hela vecka" items are standing dishes, not today's lunch; never list them as today's.
