---
name: lunch
description: Pick today's lunch in Malmö. Fetches menus from nearby restaurants, lists the user's most-visited places first, and learns from what they choose. Use when asked "where should I eat", "lunch today", "lunch in Malmö", or /lunch.
---

# Lunch in Malmö

All data and state come from `scripts/lunch.py` (path relative to this skill). Never scrape or edit prefs by hand.

## Flow

1. `python3 scripts/lunch.py menu` → JSON array. `fav: true` rows are the user's most-visited places (already sorted first); `visits` is the count. Add `--area <Area>` to filter (e.g. `Hamnen`, `Malmö Centrum`). Fields: `name`, `area`, `summary` (today's dishes), `dishes`, `visits`.
2. Print ONE plain-text list of all places, so the user can scroll it. Open with `Today is <weekday date>, N places.` Then a `**★ Most visited**` group first (only if any), then one bold group per area (`**Hamnen**`, `**Malmö Centrum**`, ...), places sorted by name. One line per place: `N. name: summary` (summary truncated ~100 chars; `standing` rows show their note); in the most-visited group add the count: `N. name (3×): summary`. Numbers run continuously across groups. Hide nothing.
3. End with one line asking which number (or name) to go to. Don't use `AskUserQuestion`: it caps at 4 options and forces paging. The user replies in chat with a number or name.
4. Report the choice: name, area, dishes. One line.
5. Record the visit: `python3 scripts/lunch.py go "<name>"`. Don't ask; this is how favorites are learned. If the user says they went somewhere else or picked by mistake: `python3 scripts/lunch.py undo "<name>"`, then `go` the right one.

## Rules

- Favorites are never set by hand: the top 5 places by visit count are listed first.
- Visit counts are per user (stored locally); don't read or edit other people's.
- Menus can be stale or missing; say so if `summary` and `dishes` are empty. Don't invent dishes.
- Fetch needs network access to `www.menydags.se` and `www.mylunch.se`.
- `standing: true` rows are fixed-menu places (no daily dishes): show the note, don't invent dishes. Picking one still counts as a visit.
