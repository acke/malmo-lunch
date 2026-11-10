---
name: lunch
description: Pick today's lunch in Malmö. Fetches menus from nearby restaurants, lists the user's favorites first, lets them choose interactively, and remembers favorites. Use when asked "where should I eat", "lunch today", "lunch in Malmö", or /lunch.
---

# Lunch in Malmö

All data and state come from `scripts/lunch.py` (path relative to this skill). Never scrape or edit prefs by hand.

## Flow

1. `python3 scripts/lunch.py menu` → JSON array, favorites (`fav: true`) first. Add `--area <Area>` to filter (e.g. `Hamnen`, `Malmö Centrum`). Fields: `slug`, `name`, `area`, `summary` (today's dishes), `dishes` (detailed, sometimes empty).
2. Print ONE numbered list of all places as plain text, so the user can scroll it. Favorites first (`★`), then the rest. Two lines per place: `N. [★ ]name [area]` then indented summary (truncate ~100 chars). Group nothing, hide nothing.
3. End with one line asking which number (or name) to go to. Don't use `AskUserQuestion`: it caps at 4 options and forces paging. The user replies in chat with a number or name.
4. Report the choice: name, area, dishes. One line.
5. If the chosen place is not a favorite, ask once whether to add it: `python3 scripts/lunch.py fav add <slug>`.

## Managing favorites

- Show: `python3 scripts/lunch.py fav list`
- Add / remove: `python3 scripts/lunch.py fav add|rm <slug>...`
- When the user says "I like X, Y" or "fav 3, 7" (numbers from the last list), match to slugs from `menu` output, then `fav add`.

## Rules

- Favorites are per user (stored locally); don't read or edit other people's.
- Menus can be stale or missing; say so if `summary` and `dishes` are empty. Don't invent dishes.
- Fetch needs network access to `www.menydags.se` and `www.mylunch.se`.
- `standing: true` rows are fixed-menu places (no daily dishes): show the note, don't invent dishes.
