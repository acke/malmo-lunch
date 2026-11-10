# malmo-lunch

Claude Code skill: pick today's lunch in Malmö (Hamnen + Centrum). Lists menus, your favorites first, you choose.

## Install

```
/plugin marketplace add acke/malmo-lunch
/plugin install malmo-lunch@malmo-lunch
```

Then ask "what's for lunch?" or run `/malmo-lunch:lunch`.

Needs Python 3 and network access to `www.menydags.se` and `www.mylunch.se`.

## Favorites

Stored per user in `~/.config/malmo-lunch/prefs.json`. Tell the skill "I like X" or pick a place and accept the "add to favorites" prompt.

Spec and contracts: [CLAUDE.md](CLAUDE.md).
