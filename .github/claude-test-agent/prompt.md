## Claude Code in CI

You run on a pull request. Edits outside the test files above are denied.

The skills are written for another agent that has a `run_tests` tool, called
with a target (`backend` or `frontend`) and test paths. Wherever a skill says
`run_tests`, run Bash from the repository root with exactly these commands;
every other shell command is denied:

- `backend`: `backend/.venv/bin/python -m pytest -q -p no:cacheprovider <test files>`
- `frontend`: `frontend/node_modules/.bin/vitest run --root frontend <test files relative to frontend/>`,
  then `frontend/node_modules/.bin/tsc --noEmit -p frontend`. vitest does not
  check types, so a frontend run passes only when both pass: fix type errors
  in your test files too.

After you finish, every test file you wrote is rerun together, so end on a run
of all of them.
