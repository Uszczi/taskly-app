# Taskly

Sample app (`frontend/`: React + TS, `backend/`: FastAPI) plus a Claude Code
workflow that writes unit tests for the code a pull request changes
(`.github/workflows/pr-test-claude.yml`):

- `.github/claude-test-agent/`: the agent itself: the `unit-test-writer` agent, skills, report
  schema, skip rules and Claude Code's settings.
- `claude-ci/`: the deterministic steps around Claude (task, coverage,
  verification, PR comment); pydantic is its only dependency. `uv run pytest` there runs its tests with no
  model or network.

The `justfile` runs the workflow's steps locally on the checked-out branch:
`just --list`.

## Two kinds of skills

- `.github/claude-test-agent/skills/` are the **test agent's** skills. The
  directory is a Claude Code plugin (`taskly-test-agent`) loaded with
  `--plugin-dir`, never through `.claude/`: claude-code-action replaces `.claude/`
  with main's copy. Edit them as prompts for that agent; `writing-for-agents`
  applies.
- `.claude/skills/` holds symlinks to vendored skills in
  `.agents/skills/`, pinned in `skills-lock.json`. Update them through the
  skills installer, not by hand.

## Where the test agent's prompt lives

Each piece has one home; change it there:

- Role, rules and Claude Code specifics (what is denied, the final rerun):
  `.github/claude-test-agent/agents/unit-test-writer.md`.
- What each report field holds: `.github/claude-test-agent/report.schema.json`.
- Testing conventions and test commands: `.github/claude-test-agent/skills/`.
- The per-run task built from a diff: `render_task` in
  `claude-ci/src/taskly_claude_ci/plan.py`.

## Files to skip

Which files need no tests is defined in three places that must change together:
`omit` in `backend/pyproject.toml`, `coverage.exclude` in
`frontend/vite.config.ts`, and `.github/claude-test-agent/skip-rules.json`.
