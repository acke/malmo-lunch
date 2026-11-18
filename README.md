# malmo-lunch

An [Agent Skills](https://agentskills.io) skill: pick today's lunch in Malmö (Hamnen + Centrum). Lists menus, your most-visited places first, you choose. Works in Claude Code, Codex, Cursor, Gemini CLI and any other agent that reads `SKILL.md`.

## Install

Any agent, via the [skills CLI](https://github.com/vercel-labs/skills):

```
npx skills add acke/malmo-lunch -a <agent> -g
```

`-g` installs for your user, without it the skill goes into the current project. Leave `-a` off to pick from the agents it detects. Restart the agent, then ask "what's for lunch?".

| Agent | `-a` | User dir | Project dir |
|---|---|---|---|
| Claude Code | `claude-code` | `~/.claude/skills/` | `.claude/skills/` |
| Codex | `codex` | `~/.agents/skills/` | `.agents/skills/` |
| Cursor | `cursor` | `~/.cursor/skills/` | `.agents/skills/` |
| Gemini CLI | `gemini-cli` | `~/.gemini/skills/` | `.agents/skills/` |
| GitHub Copilot | `github-copilot` | `~/.copilot/skills/` | `.agents/skills/` |
| OpenCode | `opencode` | `~/.config/opencode/skills/` | `.agents/skills/` |
| Amp | `amp` | `~/.config/agents/skills/` | `.agents/skills/` |
| Windsurf | `windsurf` | `~/.codeium/windsurf/skills/` | `.windsurf/skills/` |
| Goose | `goose` | `~/.config/goose/skills/` | `.goose/skills/` |

Other agents: see the [full list](https://github.com/vercel-labs/skills/blob/main/docs/agents.md).

### Manual

No Node needed. Clone, then copy `skills/lunch` into the user dir from the table (Codex shown):

```
git clone git@github.com:acke/malmo-lunch.git
mkdir -p ~/.agents/skills && cp -R malmo-lunch/skills/lunch ~/.agents/skills/
```

### Claude Code plugin

Adds the `/lunch` command on top of the skill:

```
/plugin marketplace add acke/malmo-lunch
/plugin install malmo-lunch@malmo-lunch
```

Run `/lunch` (or `/lunch Hamnen` to filter by area). If `/lunch` clashes with another command, use `/malmo-lunch:lunch`. Other agents have no slash command; ask "what's for lunch?".

## Requirements

Python 3 and network access to `www.menydags.se`, `www.mylunch.se`, `holygreens.se`, `www.clemenskott.se`, `restaurangp2.se`, `www.nordrest.se`, `miamarias.nu`.

## Favorites

Learned automatically: each time you pick a place it counts as a visit, and your 5 most-visited places are listed first. Counts are stored per user in `~/.config/malmo-lunch/prefs.json`.

Spec and contracts: [CLAUDE.md](CLAUDE.md).
