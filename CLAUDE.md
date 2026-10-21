# Taskly

Sample app (`frontend/`: React + TS, `backend/`: FastAPI) plus two independent
engines that write unit tests for it on pull requests:

- `test-agent/`: a Pydantic AI agent (`.github/workflows/pr-test-agent.yml`).
  Run it with `uv run taskly-test-agent --repo .. --help` from `test-agent/`.
- `claude-ci/`: the steps around Claude Code (`.github/workflows/pr-test-claude.yml`),
  standard library only.

They share no code, only the data in `agent-shared/`. `uv run pytest` in either
project runs its tests with no model or network.

## Two kinds of skills

- `agent-shared/skills/` are the **test engines'** skills: loaded by
  `test-agent/src/taskly_test_agent/skills.py` as deferred capabilities, and
  copied into `.claude/skills/` for Claude Code in CI. Edit them as prompts for
  those agents; `writing-for-agents` applies.
- `.claude/skills/` holds symlinks to vendored skills in
  `.agents/skills/`, pinned in `skills-lock.json`. Update them through the
  skills installer, not by hand.

## Where the prompt lives

Each piece has one home; change it there:

- Shared by both engines (`agent-shared/`): role and general rules in
  `instructions.md`, what each report field holds in `report.schema.json`,
  testing conventions in `skills/`.
- PydanticAI only: when to use a tool, in the tool's docstring in `agent.py`;
  the per-run task, in `render_task` in `changes.py`.
- Claude Code only: how its tools stand in for `run_tests`, in
  `.github/claude-test-agent/prompt.md`; the per-run task, in `render_task` in
  `claude-ci/src/taskly_claude_ci/plan.py`.

## Files to skip

Which files need no tests is defined in three places that must change together:
`omit` in `backend/pyproject.toml`, `coverage.exclude` in
`frontend/vite.config.ts`, and `agent-shared/skip-rules.json`.
