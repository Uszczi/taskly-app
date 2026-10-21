# Taskly

Sample app (`frontend/`: React + TS, `backend/`: FastAPI) plus `test-agent/`, a
Pydantic AI agent that writes unit tests for it. Run the agent with
`uv run taskly-test-agent --repo .. --help` from `test-agent/`; `uv run pytest`
there runs its own tests with no model or network.

## Two kinds of skills

- `test-agent/skills/` are the **test agent's** skills, loaded by
  `test-agent/src/taskly_test_agent/skills.py` as deferred capabilities. Edit
  them as prompts for that agent; `writing-for-agents` applies.
- `.claude/skills/` holds symlinks to vendored skills in
  `.agents/skills/`, pinned in `skills-lock.json`. Update them through the
  skills installer, not by hand.

## Where the test agent's prompt lives

Each piece has one home; change it there:

- Role and general rules: `instructions` in `agent.py`.
- When to use a tool: the tool's docstring in `agent.py`.
- The per-run task built from a diff: `render_task` in `changes.py`.
- Testing conventions: the skills in `test-agent/skills/`. They name the
  PydanticAI agent's tools; the Claude Code alternative
  (`.github/workflows/pr-test-claude.yml`) maps them to its own in
  `.github/claude-test-agent/prompt.md`.

## Files to skip

Which files need no tests is defined in three places that must change together:
`omit` in `backend/pyproject.toml`, `coverage.exclude` in
`frontend/vite.config.ts`, and the skip rules at the top of
`test-agent/src/taskly_test_agent/changes.py`.
