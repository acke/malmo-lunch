# malmo-lunch

Claude Code plugin: pick lunch in Malmö.

## Contract

- Skill `lunch` (`skills/lunch/SKILL.md`) prints one scrollable list grouped by area (most-visited group first, continuous numbering); the user replies with a number or name (no AskUserQuestion: 4-option cap); all data via `skills/lunch/scripts/lunch.py`.
- Sources (server-rendered HTML, `robots.txt` allows both, no official API, stdlib-only Python 3):
  - `https://www.menydags.se/lunch/malmo`, paginated `?sida=N`. Primary list, has area labels.
  - `https://www.mylunch.se/vastr-hamnen/` and `/malmo/`. Adds places menydags lacks (e.g. Välfärden, Orkanen) and today's real dish rows. Merged by normalized name; if it fails, menydags alone is used.
  - `skills/lunch/standing.json`: places outside the aggregators (Pink Head in Malmö Centrum; Holy Greens and Clemens in Malmö Saluhall, Hamnen). Dishes come from a scraped `menu` page (`clemens`: today's Veckans Lunchmeny block on clemenskott.se; `holygreens`: first 5 dishes on holygreens.se/meny, chain-wide) or a hand-kept `dishes` list (Pink Head: its menu loads client-side from weiq.app behind credentials, so the list is hand-kept from its own Lunch menu, veg variants collapsed; it ages, refresh it by reading weiq.app/pinkhead1/meny in a browser). `fixed: true` = no daily lunch, regular menu; such rows get `standing: true`. `note` is shown only when no dishes are found.
- lunchmap.se is not usable: dishes render client-side and `/api/` is disallowed.
- `lunch.py menu [--area NAME]` → JSON list `{slug, name, area, dishes[{name,desc,price}], summary, visits, fav, standing?}`. `fav` = one of the 5 most-visited places (by `visits`), listed first in visit order; then the rest by name. Restaurants with no menu today are dropped, as are areas too far from the office (Hyllie, Limhamn, Möllevången).
- Same place on several sources is merged by a normalized name (drops words like restaurang, brasserie, hotel, malmö, 1912). `summary` is up to 6 dish names with ingredient lists cut (`med ...`, comma lists), taken from whichever of the teaser / dish rows names more dishes. Source noise is filtered: section labels, "Serveras ..." and English translation rows, allergen codes, à-la-carte rows with a price, weekday prefixes.
- `standing.json` wins over scraped rows of the same name. Always show dish names, never meta notes like "menu unreliable": La Fonderie, Ruths and Saltimporten show their scraped dishes.
- `lunch.py go NAME` records a visit; `lunch.py undo NAME` removes one. Favorites are learned from visits, never set by hand. The skill calls `go` after the user picks a place.
- Prefs: `$XDG_CONFIG_HOME/malmo-lunch/prefs.json` (default `~/.config/malmo-lunch/prefs.json`), `{"visits": {normalized-name: count}}`. Keyed by the same normalized name used for merging sources, so counts survive a place moving between sources. One file per user; nothing shared.
- Network: `www.menydags.se`, `www.mylunch.se`, `holygreens.se`, `www.clemenskott.se`.

## Rules

- Don't add other sources/caches unless menydags breaks; if the HTML changes, fix the regexes in `lunch.py`.
- "Gäller hela vecka" items are standing dishes, not today's lunch; never list them as today's.
