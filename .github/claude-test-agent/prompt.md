## Claude Code in CI

You run on a pull request. Edits outside the test files above are denied, and
so is every shell command other than the test and typecheck commands in the
backend and frontend skills.

After you finish, every test file you wrote is rerun together, so end on a run
of all of them.
