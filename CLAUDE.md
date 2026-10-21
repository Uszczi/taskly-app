# Taskly

Sample app (`frontend/`: React + TS, `backend/`: FastAPI) plus a Claude Code
workflow that writes unit tests for the code a pull request changes
(`.github/workflows/pr-test-claude.yml`):

- `agent-shared/`: the agent's data: skills, instructions, report schema, skip
  rules and the coverage script.
- `claude-ci/`: the deterministic steps around Claude (task, verification, PR
  comment), standard library only. `uv run pytest` there runs its tests with no
  model or network.

## Two kinds of skills

- `agent-shared/skills/` are the **test agent's** skills, copied into
  `.claude/skills/` for Claude Code in CI. Edit them as prompts for that agent;
  `writing-for-agents` applies.
- `.claude/skills/` holds symlinks to vendored skills in
  `.agents/skills/`, pinned in `skills-lock.json`. Update them through the
  skills installer, not by hand.

## Where the test agent's prompt lives

Each piece has one home; change it there:

- Role and general rules: `agent-shared/instructions.md`.
- What each report field holds: `agent-shared/report.schema.json`.
- Testing conventions and test commands: `agent-shared/skills/`.
- Claude Code specifics (what is denied, the final rerun):
  `.github/claude-test-agent/prompt.md`.
- The per-run task built from a diff: `render_task` in
  `claude-ci/src/taskly_claude_ci/plan.py`.

## Files to skip

Which files need no tests is defined in three places that must change together:
`omit` in `backend/pyproject.toml`, `coverage.exclude` in
`frontend/vite.config.ts`, and `agent-shared/skip-rules.json`.
