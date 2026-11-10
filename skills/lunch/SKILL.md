---
name: lunch
description: "Pick where to eat lunch today near the Neo4j office in Malmö (Hamnen, Malmö Centrum). Fetches today's menus from ~40 restaurants, lists the user's most-visited places first, lets them choose, and learns favorites from the choice. Use whenever the user asks 'what's for lunch', 'where should we eat', 'lunch today', 'dagens lunch', 'vad ska vi äta', 'any good lunch places nearby', or types /lunch, even if they don't say Malmö. Not for cooking at home or meal planning. Produces one scrollable numbered list of places with today's dishes, then records the pick."
---

# Lunch in Malmö

You are the colleague who knows what every place near the office serves today. The value is one list the user can scan in seconds and answer with a number.

The script `scripts/lunch.py` (relative to this skill's base directory) fetches every menu live and builds the whole list, so the places and dishes are always today's and the list looks the same each run. Don't scrape pages, rebuild the list yourself, or edit `prefs.json`.

## Flow

1. Run `python3 scripts/lunch.py list`. Add `--area <Area>` only if the user named one (`Hamnen`, `Malmö Centrum`; `/lunch Hamnen` passes it as an argument).
2. Print the script's output as your reply, unchanged, as plain chat text. It already ends with the question. Don't use `AskUserQuestion` here: it takes at most 4 options, which forces paging through 40 places, while one long list can be scrolled.
3. When the user answers with a number or name, report the choice in one line (name, area, dishes from the list) and record it: `python3 scripts/lunch.py go "<name>"`. Don't ask first. The counts are how favorites are learned, and a confirmation step would make people skip it.
4. If they say they went somewhere else, or picked wrong: `python3 scripts/lunch.py undo "<name>"`, then `go` the right one.

## When things go wrong

- **Output starts with `ERROR:`** or the script crashes: tell the user the menus can't be fetched right now and name the host from the error. Don't make up a list.
- **Output says no places were found** (weekend or holiday): say there's no lunch data today.
- **User asks for tomorrow or another day:** not supported. Say so and offer today.
- **User's answer doesn't match a line:** ask which of the closest matches they meant; don't `go` a guess.
- **A "(fast meny)" place** has a regular menu, not a daily lunch; say so if asked.

## Anti-patterns

- Retyping, reordering, shortening or "improving" the list.
- Calling `go` when the user is only browsing ("what's there?") and hasn't chosen.
- Adding a manual "save favorite" step. Favorites come from visits only.
- Reading or showing another person's `prefs.json`.
