# malmo-lunch

Claude Code skill: pick today's lunch in Malmö (Hamnen + Centrum). Lists menus, your most-visited places first, you choose.

## Install

```
/plugin marketplace add acke/malmo-lunch
/plugin install malmo-lunch@malmo-lunch
```

Then run `/lunch` (or `/lunch Hamnen` to filter by area), or just ask "what's for lunch?". If `/lunch` clashes with another command, use `/malmo-lunch:lunch`.

### Other agents (Codex, Cursor, Gemini CLI, ...)

`skills/lunch/` is a plain [Agent Skills](https://agentskills.io) folder, so any agent that reads `SKILL.md` can use it. No slash command outside Claude Code; ask "what's for lunch?".

```
npx skills add acke/malmo-lunch -a codex
```

Swap `codex` for `cursor`, `gemini-cli`, etc., or leave `-a` off to pick interactively. Manual install for Codex:

```
git clone git@github.com:acke/malmo-lunch.git
mkdir -p ~/.agents/skills && cp -R malmo-lunch/skills/lunch ~/.agents/skills/
```

Restart the agent. Other agents: copy `skills/lunch` into that agent's skills directory.

Needs Python 3 and network access to `www.menydags.se`, `www.mylunch.se`, `holygreens.se`, `www.clemenskott.se`.

## Favorites

Learned automatically: each time you pick a place it counts as a visit, and your 5 most-visited places are listed first. Counts are stored per user in `~/.config/malmo-lunch/prefs.json`.

Spec and contracts: [CLAUDE.md](CLAUDE.md).
