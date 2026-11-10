# malmo-lunch

Claude Code plugin: pick lunch in Malmö.

## Contract

- Skill `lunch` (`skills/lunch/SKILL.md`) drives an interactive pick; all data via `skills/lunch/scripts/lunch.py`.
- Sources (server-rendered HTML, `robots.txt` allows both, no official API, stdlib-only Python 3):
  - `https://www.menydags.se/lunch/malmo`, paginated `?sida=N`. Primary list, has area labels.
  - `https://www.mylunch.se/vastr-hamnen/` and `/malmo/`. Adds places menydags lacks (e.g. Välfärden, Orkanen) and today's real dish rows. Merged by normalized name; if it fails, menydags alone is used.
  - `skills/lunch/standing.json`: fixed-menu places with no daily lunch (Pink Head, Saluhall stalls). Shown with `standing: true` and a note; edit the file to add more.
- lunchmap.se is not usable: dishes render client-side and `/api/` is disallowed.
- `lunch.py menu [--area NAME]` → JSON list `{slug, name, area, dishes[{name,desc,price}], summary, fav, standing?}`. Favorites first, then by name. Restaurants with no menu today are dropped, as are areas too far from the office (Hyllie, Limhamn, Möllevången).
- `lunch.py fav list|add|rm SLUG...` → prints favorites JSON.
- Prefs: `$XDG_CONFIG_HOME/malmo-lunch/prefs.json` (default `~/.config/malmo-lunch/prefs.json`), `{"favorites": [slug]}`. One file per user; nothing shared.
- Network: `www.menydags.se`, `www.mylunch.se`.

## Rules

- Don't add other sources/caches unless menydags breaks; if the HTML changes, fix the regexes in `lunch.py`.
- "Gäller hela vecka" items are standing dishes, not today's lunch; never list them as today's.
