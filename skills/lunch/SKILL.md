---
name: lunch
description: "Pick where to eat lunch today near the Neo4j office in Malmö (Hamnen, Malmö Centrum). Fetches today's menus from ~40 restaurants, lists the user's most-visited places first, lets them choose, and learns favorites from the choice. Use whenever the user asks 'what's for lunch', 'where should we eat', 'lunch today', 'dagens lunch', 'vad ska vi äta', 'any good lunch places nearby', or types /lunch, even if they don't say Malmö. Not for cooking at home or meal planning. Produces one scrollable numbered list of places with today's dishes, then records the pick."
---

# Lunch in Malmö

You are the colleague who knows what every place near the office serves today. The value is a single list the user can scan in seconds and answer with a number.

All data and state come from `scripts/lunch.py`, relative to this skill's base directory. Scraping and the user's visit history live in that script so the list is consistent between runs; don't scrape pages or edit `prefs.json` yourself.

## Flow

1. Run `python3 scripts/lunch.py menu`. Add `--area <Area>` only if the user named one (`Hamnen`, `Malmö Centrum`; `/lunch Hamnen` passes it as an argument). It returns a JSON array. Fields: `name`, `area`, `summary` (today's dishes), `dishes`, `visits`, `fav` (true for the user's 5 most-visited places, already sorted first), `standing` (fixed-menu place).
2. Print the list using the template below, then ask which one.
3. When the user answers, report the choice in one line and record it: `python3 scripts/lunch.py go "<name>"`. Don't ask first. The counts are how favorites are learned, and a confirmation step would make people skip it.
4. If they say they went somewhere else, or picked wrong: `python3 scripts/lunch.py undo "<name>"`, then `go` the right one.

## Output template

Print this as plain chat text, not a picker. A picker (`AskUserQuestion`) takes at most 4 options, which forces paging through 40 places; one long list can be scrolled.

```
Today is Tue 2026-11-10, 41 places.

**★ Most visited**
1. Välfärden (3×): Bakad lax · Pasta i tomatsås

**Hamnen**
2. Hörnet: Stekt sill
3. Holy Greens (fast meny): Harvest bowl · Seoul bowl · Thai-ish

**Malmö Centrum**
4. Bullen - Två Krögare: Tempurafriterad kolja · Kalvköttbullar

Which number (or name) are you going to?
```

- The most-visited group appears only when some place has visits; its lines carry the count.
- Then one bold group per area in the order the data gives, places sorted by name.
- One line per place: `N. name: summary`, summary cut at about 100 characters. Numbers run continuously across groups.
- Mark `standing: true` rows `(fast meny)`: their dishes are the regular menu, not a daily lunch.
- Show every place. A shortened list hides the one the user was thinking of.
- Keep dish names in Swedish as the data has them; write the rest in the user's language.

## When things go wrong

- **Script error or no network:** say which host failed (the error names it) and that the list can't be built right now. Don't make up a list. The script needs `www.menydags.se`, `www.mylunch.se`, `holygreens.se` and `www.clemenskott.se`.
- **Weekend or holiday, few or zero places:** say there's little or no lunch data today instead of presenting an empty list as normal.
- **A place with an empty `summary`:** list it with "no menu found today". Never invent dishes.
- **"Tomorrow" or another day:** not supported. Say so and offer today.
- **Name not in the list** when the user answers: ask which of the closest matches they meant; don't `go` a guess.

## Quality checks

- The list is one message, grouped as in the template, with continuous numbers.
- No place is dropped and no dish is invented.
- `go` is called exactly once per choice, and only after the user picked.
- The user's last line asks for a number or name.

## Anti-patterns

- Paging through places with `AskUserQuestion`.
- Calling `go` when the user was only browsing ("what's there?") and hasn't chosen.
- Listing favorites without the visit count, or adding a manual "save favorite" step. Favorites come from visits only.
- Reading or showing another person's `prefs.json`.
