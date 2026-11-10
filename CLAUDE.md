# malmo-lunch

Claude Code plugin: pick lunch in Malmö.

## Contract

- Skill `lunch` (`skills/lunch/SKILL.md`) prints one scrollable list grouped by area (favorites group first, continuous numbering); the user replies with a number or name (no AskUserQuestion: 4-option cap); all data via `skills/lunch/scripts/lunch.py`.
- Sources (server-rendered HTML, `robots.txt` allows both, no official API, stdlib-only Python 3):
  - `https://www.menydags.se/lunch/malmo`, paginated `?sida=N`. Primary list, has area labels.
  - `https://www.mylunch.se/vastr-hamnen/` and `/malmo/`. Adds places menydags lacks (e.g. Välfärden, Orkanen) and today's real dish rows. Merged by normalized name; if it fails, menydags alone is used.
  - `skills/lunch/standing.json`: fixed-menu places with no daily lunch (Pink Head, Saluhall stalls). Shown with `standing: true` and a note; edit the file to add more.
- lunchmap.se is not usable: dishes render client-side and `/api/` is disallowed.
- `lunch.py menu [--area NAME]` → JSON list `{slug, name, area, dishes[{name,desc,price}], summary, fav, standing?}`. Favorites first, then by name. Restaurants with no menu today are dropped, as are areas too far from the office (Hyllie, Limhamn, Möllevången).
- Same place on several sources is merged by a normalized name (drops words like restaurang, brasserie, hotel, malmö, 1912). `summary` is up to 6 dish names with ingredient lists cut (`med ...`, comma lists), taken from whichever of the teaser / dish rows names more dishes. Source noise is filtered: section labels, "Serveras ..." and English translation rows, allergen codes, à-la-carte rows with a price, weekday prefixes.
- `standing.json` wins over scraped rows of the same name, also for places whose scraped menu is unreliable (La Fonderie, Ruths, Saltimporten).
- `lunch.py fav list|add|rm SLUG...` → prints favorites JSON.
- Prefs: `$XDG_CONFIG_HOME/malmo-lunch/prefs.json` (default `~/.config/malmo-lunch/prefs.json`), `{"favorites": [slug]}`. One file per user; nothing shared.
- Network: `www.menydags.se`, `www.mylunch.se`.

## Rules

- Don't add other sources/caches unless menydags breaks; if the HTML changes, fix the regexes in `lunch.py`.
- "Gäller hela vecka" items are standing dishes, not today's lunch; never list them as today's.
