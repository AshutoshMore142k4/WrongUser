# Install

The skill is the [`skills/wronguser/`](skills/wronguser/) folder (SKILL.md + references/ + scripts/).

- **skills.sh:** `npx skills add AshutoshMore142k4/WrongUser` ([listing](https://www.skills.sh/ashutoshmore142k4/wronguser/wronguser))
- **Claude Code, by hand:** copy `skills/wronguser/` to `~/.claude/skills/wronguser/` (all projects) or `.claude/skills/wronguser/` (one project).
- **claude.ai:** zip the `wronguser/` folder (folder at the zip root) and upload under Settings → Capabilities → Skills.
- **API:** upload the same folder through the Skills API.

Requires Python 3.9+ for the optional scanner; everything else uses your repo's own test framework.
