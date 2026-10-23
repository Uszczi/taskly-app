# SOLUTION_LONG.md

## Technical decisions and rationale
- Workflows stay simple and hold no logic, because workflows are hard to test locally.
- A small Python CLI (claude-ci) holds the logic.
- The solution has as little code as possible, so there is less to maintain and fewer places for bugs.
- The agent's commands and the verification rerun run in sandboxes without network and secrets, which limits what a malicious agent can damage.
- The agent's permissions are as narrow as possible. It edits only test files, runs only the test and typecheck commands in Bash, reads everything except `.env` files and `.git`, and has no web access.
- The workflow does not trust model output. claude-ci checks that the agent changed only test files, and it counts deletes, renames and symlinks as violations too (fail closed).
- claude-ci gives the agent the exact files to work on, so the agent spends fewer turns on discovery. Each file comes with its diff, cut at 6000 characters, and the agent reads the rest itself.
- The agent decides whether to split a task between subagents, e.g. for a big PR or to keep frontend and backend context apart. Subagents run in parallel and in the foreground, because in a non-interactive session a background subagent never finishes.
- The workflow has two jobs. The first has read access and runs the agent. The second has write access and runs no code from the PR.
- The workflow opens a new PR with the tests, so a person reviews it and decides whether to merge. Every new commit to the PR starts the workflow again, and it opens another tests PR when there is something to test.
- The agent's definition says that all text in the repository is data written by the PR's author, and that the agent never follows instructions inside it.
- The justfile runs the workflow's steps locally, as close to GitHub Actions as possible.
- The report shows coverage before and after the agent's tests.
- The workflow fails when the rerun of the tests fails, when the agent changed anything but tests, or when the agent failed, gave an invalid report, or reported tests it never wrote (e.g. because the permissions denied its edits). The rerun covers the whole suite of each area the agent wrote tests in, plus the frontend typecheck.
- The agent cannot reach secrets. `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` removes them from the commands the agent runs, and the sandbox denies `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `GH_TOKEN` and the Actions tokens.
- claude-ci verifies the tests without the model. It reruns the tests and measures coverage with `env -i` and bubblewrap, with no network, a read-only filesystem except the checkout, and a 600 s timeout per command. The workflow installs claude-ci outside the checkout before the agent runs, so the agent cannot change it.
- Model text never reaches a shell. The agent's report goes through an environment variable, multi-line step outputs use a random delimiter, and claude-ci validates the base ref before passing it to git.
- claude-ci validates the agent's report with pydantic, even though the action already checks it against the JSON schema. An invalid report fails the run.
- claude-ci cleans model text before the workflow posts it, removing HTML and `@` mentions and escaping table separators.
- The workflow keeps cost down. When no changed file needs tests, the agent does not run at all. A new push cancels the run in progress. The job times out after 30 minutes and the agent after 200 turns.
- Failures stay visible. The PR gets a comment that explains what failed, including how many tool calls Claude Code denied. The run keeps logs, the patch, the results and the agent's full transcript (`execution.json`) as artifacts for 14 days, and the job summary has the report too.


## Prerequisites and how to run the workflow on GitHub Actions
- Create the environment `CI` and add the secret `ANTHROPIC_API_KEY` to it.
  `Settings > Environments`
- Optionally set the repository variable `CLAUDE_MODEL` (default `claude-haiku-5-5`).
  `Settings > Secrets and variables > Actions > Variables`
- To run a PR on Sonnet instead, add the label `sonnet` to it. Create the label once with `gh label create sonnet`. Adding the label starts a run. The tests PR's branch and title name the model, so you can compare both models on the same commit.
- Allow GitHub Actions to create and approve pull requests.
  `Settings > Actions > General`
- The workflow runs on every pull request from a branch of this repository, not from forks.
- The workflow runs again on every new commit to the PR.

## Prerequisites and how to run the workflow locally
The justfile reproduces the workflow locally, except for opening the tests PR and posting the comment.
You can run it as many times as you need.
- Install just, uv, Node and npm, jq, bubblewrap, socat and claude (logged in).
- Install the backend and frontend dependencies with `just ci-setup`.
- Run all steps with `just ci`.
- See the `justfile` for the individual steps.


## Solution
- The workflow is `.github/workflows/pr-test-claude.yml`.
- `.github/claude-test-agent/agents/unit-test-writer.md` defines the custom agent `unit-test-writer`: its role, rules and steps, and when to split work between subagents.
  `.github/claude-test-agent/` is a Claude Code plugin named `taskly-test-agent`. Claude Code runs with `--plugin-dir .github/claude-test-agent --agent taskly-test-agent:unit-test-writer`. When the agent decides a PR is too big, it dispatches `taskly-test-agent:unit-test-writer` subagents, so every slice follows the same rules.
  The workflow does not copy the agent into `.claude/`, because claude-code-action replaces `.claude/` with the copy from `main` (it treats the PR head as untrusted).
- The prompt is only the task that claude-ci generates: the exact files to work on, their diffs and their test paths.
- `.github/claude-test-agent/skills/` holds the agent's skills, and they come with the plugin (`taskly-test-agent:test-scope` and so on).
- `.github/claude-test-agent/settings.json` holds the Claude Code settings.
- `.github/claude-test-agent/report.schema.json` is the schema of the agent's report.

There are three skills. The agent's definition tells the agent to load them, but nothing enforces it, and `skills_used` in the report is the agent's own claim.
* `test-scope`, loaded first when there are changes, helps the agent decide what to do with each changed file the plan did not skip.
* `backend-unit-tests`, loaded before the agent writes or updates any backend test.
* `frontend-unit-tests`, loaded before the agent writes or updates any frontend test.

## Steps of the workflow
### Generate (read access)
1. Prepare directories
2. Check out the PR's head commit
3. Set up Python
4. Install claude-ci
5. Generate the prompt with claude-ci

Steps 6 to 12 run only when a changed file needs tests.

6. Install bubblewrap for the sandbox
7. Set up Node
8. Install the frontend and backend dependencies
9. Measure coverage before, with claude-ci
10. Run the agent (`unit-test-writer`)
11. Verify the generated tests with claude-ci
12. Measure coverage after, with claude-ci
13. Prepare the PR comment
14. Upload artifacts
15. Fail the job when tests fail, when the agent changed something other than tests, or when the agent failed or wrote none of the tests it reported
### Publish (write access)
16. Download artifacts
17. Check out the PR's head commit
18. Open a new PR with the tests
19. Post a comment on the source PR


## Example run

PR [#11](https://github.com/Uszczi/taskly-app/pull/11) adds a task summary and clearing of completed tasks, with 15 changed files in the backend and frontend.
The workflow ran on it once per model, and each run opened its own tests PR.

| | Haiku | Sonnet |
|---|---|---|
| Tests PR | [#15](https://github.com/Uszczi/taskly-app/pull/15) | [#14](https://github.com/Uszczi/taskly-app/pull/14) |
| Run | [39943175921](https://github.com/Uszczi/taskly-app/actions/runs/39943175921) | [39942212032](https://github.com/Uszczi/taskly-app/actions/runs/39942212032) |
| Commit of #11 | `a945f7f` | `90cc090` |
| Status | ok | ok |
| Tests added | 33 in 14 files | 26 in 14 files |
| Rerun by verify (its logs) | backend 34 passed, frontend 41 passed, typecheck clean | backend 28 passed, frontend 42 passed, typecheck clean |
| Backend coverage | 43.9% to 49.2% | 43.9% to 49.2% |
| Frontend coverage | 39.8% to 66.3% | 39.8% to 66.3% |
| Cost, turns | $0.046, 62 turns | $0.32, 42 turns |
| Denied tool calls | 5 | 1 |

**Agent's decisions.** Both runs made the same decisions for the 12 files in scope.
- `add` for the new files `stats.py`, `TodoSummary.tsx` and the five hooks.
- `update` for the files that already had tests: `repository.py`, `router.py`, `TodosPage.tsx`, `api/todos.ts` and `utils/todos.ts`.
- No tests for `schemas.py`, `queryKeys.ts` and `types.ts`, which the plan skipped because coverage excludes them.
- One copy of shared test code: a query client helper (`frontend/src/test/queryClient.tsx`) and a stats fixture (`frontend/src/test/statsFixture.ts`).

**Skills used.** Both runs loaded `test-scope`, `backend-unit-tests` and `frontend-unit-tests`. The Skill tool calls in the agent's transcript (`execution.json`) confirm it, not only the agent's report.

**Subagents.** Neither run used subagents; the agent did all 12 files itself.

**Denied tool calls.** Sonnet tried to append to a test file through Bash (`tee -a ...`). The permissions refused the call, and the agent used Edit instead. Haiku had five Write and Edit calls on test files refused (`queryClient.tsx`, `statsFixture.ts`, `test_stats.py`, `api/todos.test.ts`), yet those files are in the tests PR, so later calls succeeded. The transcript does not show why the first calls were refused.

**Comparison of the models.** Both models covered every changed file, reached the same coverage and passed verification. Haiku wrote more, narrower tests and listed under *Needs your attention* what it could not pin, such as the real `date.today()` wiring and the order of `cancelQueries` before the cache update. Sonnet wrote fewer, broader tests at about 7 times the cost.

**Test style.** The generated tests follow the existing ones. The backend tests are plain functions named after the behavior (e.g. `test_completion_rate_is_rounded_to_two_decimals`) that use the shared fixtures. The frontend tests use `it(...)` blocks, `todoFixture`, the design-system mock, `userEvent` and role queries, and no `any`. Every stats object in the tests spreads the shared fixture (`{ ...statsFixture, completion_rate: 0 }`) instead of building one inline.


## Assumptions
- PR authors are trusted. The workflow runs only for branches of this repository.
- A person reviews every tests PR and decides whether to merge it. Nothing merges automatically.
- The existing test suites pass on the PR's base, since verify reruns the whole suite of each area the agent wrote tests in.
- The agent writes unit tests only, for `backend/app` with pytest and `frontend/src` with vitest. It follows the repository's layout: backend tests mirror the source path under `backend/tests/` with a `test_` prefix, and frontend tests sit next to the source.
- The files that need no tests are the ones coverage excludes (`backend/pyproject.toml`, `frontend/vite.config.ts`), and `skip-rules.json` mirrors them.
- Tests run offline, and they mock everything they would reach over the network.
- CI runs on GitHub-hosted Ubuntu 24.04 runners, where bubblewrap can be installed.

## Limitations
- It works only with Claude.
- After the agent writes tests, verify requires every test in the area to pass, including tests that were already failing.
- The agent runs in a sandbox without internet access or external documentation.
- Someone has to close unmerged tests PRs by hand. Every commit to the branch can open a new tests PR, and usually only the last one is useful.
- The agent can edit only test files, even when the fix in production code is simple.
- The results depend heavily on the model.
- Price and time grow with the size of the PR. Only the turn limit and the timeout cap them.
- The workflow needs bubblewrap for the sandbox, so it does not run on macOS.
- The test commands are defined in several places: `settings.json`, both test skills, `verify.py` and `coverage.py`.

## What to do before production
- Open the tests PR with a GitHub App token instead of the Actions token. Pull requests opened with the Actions token start no workflows.
- Run the app's own test suites (pytest, vitest and the typecheck) on every PR in a separate workflow, so a red suite is visible without the agent.
- Keep one tests PR per source PR and update it on every push, closing the ones a new push replaces. Update one comment on the source PR instead of adding a new one per push.
- Skip draft PRs and PRs from bots such as Dependabot, which have no access to the API key and always end as `agent_failed`.
- Set a budget per run: a cost cap, and a size limit above which the workflow skips the agent and says why.
- Make sure the Claude Code version cannot change between two runs. Both example runs installed 2.1.306, but the workflow does not pin it; `path_to_claude_code_executable` lets it install and pin its own.
- Escape the PR's file names in the report the same way as model text.
- Check that the report has a decision for every file in the plan, and fail the run when one is missing.
- Track cost, turns and denied tool calls per run, to see when the model or a prompt change makes runs worse.

## What to do next
- Run the agent once over all source files of the existing app, not only over a PR's diff, to add the tests the app still lacks.
- Read the skills the agent loaded from its transcript instead of its report, and show the decisions and skills in the PR comment.
- Run different models in parallel and compare their tests in one comment.
- Add an agent that reviews the generated tests PR.
- Give each push only the commits since the last run, so a new tests PR does not repeat the previous one.
- Define the test commands in one place and generate `settings.json`, the skills' run commands and claude-ci's commands from it.
