# malmo-lunch

Claude Code plugin: pick lunch in Malmö.

## Contract

- Skill `lunch` (`skills/lunch/SKILL.md`) drives an interactive pick; all data via `skills/lunch/scripts/lunch.py`.
- Source: `https://www.menydags.se/lunch/malmo` (server-rendered HTML, paginated `?sida=N`, `robots.txt` allows `/lunch`). No official API. Stdlib-only Python 3.
- `lunch.py menu [--area NAME]` → JSON list `{slug, name, area, dishes[{name,desc,price}], summary, fav}`. Favorites first, then by name. Restaurants with no menu today are dropped, as are areas too far from the office (Hyllie, Limhamn, Möllevången).
- `lunch.py fav list|add|rm SLUG...` → prints favorites JSON.
- Prefs: `$XDG_CONFIG_HOME/malmo-lunch/prefs.json` (default `~/.config/malmo-lunch/prefs.json`), `{"favorites": [slug]}`. One file per user; nothing shared.
- Network: only `www.menydags.se`.

## Rules

- Don't add other sources/caches unless menydags breaks; if the HTML changes, fix the regexes in `lunch.py`.
- "Gäller hela vecka" items are standing dishes, not today's lunch; never list them as today's.
