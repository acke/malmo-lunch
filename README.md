# malmo-lunch

Claude Code skill: pick today's lunch in Malmö (Hamnen + Centrum). Lists menus, your most-visited places first, you choose.

## Install

```
/plugin marketplace add acke/malmo-lunch
/plugin install malmo-lunch@malmo-lunch
```

Then run `/lunch` (or `/lunch Hamnen` to filter by area), or just ask "what's for lunch?". If `/lunch` clashes with another command, use `/malmo-lunch:lunch`.

Needs Python 3 and network access to `www.menydags.se`, `www.mylunch.se`, `holygreens.se`, `www.clemenskott.se`.

## Favorites

Learned automatically: each time you pick a place it counts as a visit, and your 5 most-visited places are listed first. Counts are stored per user in `~/.config/malmo-lunch/prefs.json`.

Spec and contracts: [CLAUDE.md](CLAUDE.md).
