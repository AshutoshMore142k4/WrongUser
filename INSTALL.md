# Install

The skill is the `nosy/` folder (SKILL.md + references/ + scripts/).

- **Claude Code:** copy `nosy/` to `~/.claude/skills/nosy/` (all projects) or `.claude/skills/nosy/` (one project).
- **claude.ai:** zip the `nosy/` folder (folder at the zip root) and upload under Settings → Capabilities → Skills.
- **API:** upload the same folder through the Skills API.

Requires Python 3.9+ for the optional scanner; everything else uses your repo's own test framework.
