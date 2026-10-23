# SOLUTION.md

A GitHub Actions workflow runs a Claude Code agent on every pull request. The agent writes unit tests for the changed backend and frontend code, claude-ci reruns them without the model, and the workflow opens a separate PR with the tests and the results.
[SOLUTION_LONG.md](SOLUTION_LONG.md) has the full details.

## Technical decisions
- The workflow holds no logic. A small Python CLI, claude-ci, plans the task, verifies the agent's work, measures coverage and writes the report.
- The workflow has two jobs. The first runs the agent with read access only. The second has write access, runs no code from the PR, and opens the tests PR.
- The agent may edit only test files and run only the test commands. Its commands run in a sandbox without network and secrets.
- The workflow does not trust the model. claude-ci reruns the tests in its own sandbox, rejects any change that is not a test file, and validates the agent's report.
- claude-ci gives the agent the exact changed files and their diffs, so it spends few turns on discovery.
- The agent decides whether to split a big PR between subagents.
- Model text never reaches a shell, and the workflow cleans it before posting it.
- A person reviews and merges the tests PR; nothing merges automatically.

## How to run it
On GitHub:
- Create the environment `CI` with the secret `ANTHROPIC_API_KEY`.
- Allow GitHub Actions to create pull requests (`Settings > Actions > General`).
- Open a PR from a branch of this repository. The workflow uses Haiku; the label `sonnet` reruns it with Sonnet.

Locally, with just, uv, Node, jq, bubblewrap, socat and a logged-in claude: `just ci-setup`, then `just ci`.

## Where the agent and skills are
- `.github/claude-test-agent/` is a Claude Code plugin. The workflow loads it with `--plugin-dir`.
- `agents/unit-test-writer.md` defines the agent: role, rules and steps.
- `skills/` holds three skills: `test-scope` decides what to test, `backend-unit-tests` and `frontend-unit-tests` hold each area's conventions and commands.
- `settings.json` holds the agent's permissions and sandbox, and `report.schema.json` the shape of its report.

## Example run
PR [#11](https://github.com/Uszczi/taskly-app/pull/11) adds a task summary and clearing of completed tasks (15 files). The workflow ran once per model:

| | Haiku | Sonnet |
|---|---|---|
| Tests PR | [#15](https://github.com/Uszczi/taskly-app/pull/15) | [#14](https://github.com/Uszczi/taskly-app/pull/14) |
| Tests added | 33 | 26 |
| Rerun by verify | backend 34, frontend 41 passed, typecheck clean | backend 28, frontend 42 passed, typecheck clean |
| Coverage, backend and frontend | 43.9% to 49.2%, 39.8% to 66.3% | the same |
| Cost | $0.046 | $0.32 |

Both runs loaded all three skills and made the same decisions: `add` for 7 new files, `update` for 5 files that had tests, and no tests for 3 files that coverage excludes. The tests follow the repository's existing style.

## Assumptions
- PR authors are trusted; the workflow runs only for branches of this repository.
- The existing test suites pass before the PR.
- Unit tests only, for `backend/app` (pytest) and `frontend/src` (vitest). Files excluded from coverage need no tests.

## Limitations
- Works only with Claude, and the results depend on the model.
- Every test in a changed area must pass, including tests that were already failing.
- Every commit can open a new tests PR, and old ones need closing by hand.
- No checks run on the tests PR itself.
- The existing app was not backfilled with tests; the agent only covers PR changes.

## Before production
- Open the tests PR with a GitHub App token, so checks run on it.
- Keep one tests PR and one comment per source PR, updated on every push.
- Add a cost cap and a size limit per run, and pin the Claude Code version.
- Check that the report has a decision for every planned file.
