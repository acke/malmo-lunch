---
name: lunch
description: Pick today's lunch in Malmö. Fetches menus from nearby restaurants, lists the user's favorites first, lets them choose interactively, and remembers favorites. Use when asked "where should I eat", "lunch today", "lunch in Malmö", or /lunch.
---

# Lunch in Malmö

All data and state come from `scripts/lunch.py` (path relative to this skill). Never scrape or edit prefs by hand.

## Flow

1. `python3 scripts/lunch.py menu` → JSON array, favorites (`fav: true`) first. Add `--area <Area>` to filter (e.g. `Hamnen`, `Malmö Centrum`). Fields: `slug`, `name`, `area`, `summary` (today's dishes), `dishes` (detailed, sometimes empty).
2. Show a short numbered list: `★` for favorites, name, area, summary. Favorites on top.
3. Ask which to go to with `AskUserQuestion`: favorites first, max 4 options per question; put "Show more" as the last option and page through the rest. Offer area filter if the list is long.
4. Report the choice: name, area, dishes. One line.
5. If the chosen place is not a favorite, ask once whether to add it: `python3 scripts/lunch.py fav add <slug>`.

## Managing favorites

- Show: `python3 scripts/lunch.py fav list`
- Add / remove: `python3 scripts/lunch.py fav add|rm <slug>...`
- When the user says "I like X, Y", match names to slugs from `menu` output, then `fav add`.

## Rules

- Favorites are per user (stored locally); don't read or edit other people's.
- Menus can be stale or missing; say so if `summary` and `dishes` are empty. Don't invent dishes.
- Fetch needs network access to `www.menydags.se` and `www.mylunch.se`.
- `standing: true` rows are fixed-menu places (no daily dishes): show the note, don't invent dishes.
