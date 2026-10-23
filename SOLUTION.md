# SOLUTION.md

## Technical Decisions and Rationale
- Workflows try to be simple and don't hold logic. It's hard to test them locally.
- For complex behaviour there is a small Python CLI.
- As little code as possible so there is less to maintain and fewer possible bugs.
- The agent's commands and the verification rerun run in sandboxes without network and secrets, so the possible damage by a malicious agent is smaller.
- Permissions of agent are as restricted as possible: edits only to test files, Bash only for the test and typecheck commands, reads everywhere except `.env` files and `.git`, no web access.
- Don't trust model output, e.g validate programmatically that agent updated only tests. Deletes, renames and symlinks count as violations too (fail closed).
- Provide agent exact files to investigate so there is less discovery. Each file comes with its diff (cut at 6000 characters; the agent reads the rest itself).
- Agent decides itself whether to split a task into subagents, e.g. for a big PR or to separate frontend and backend context. Subagents run in the foreground, in parallel: in a non-interactive session a background subagent never finishes.
- Workflow is divided into two parts, first with read access which runs Agent, second one has write access without any code execution
- Workflow creates a new PR so user reviews and merge or not. If not happy with the result, a new commit to the PR runs the workflow again and creates another PR.
- If PR is updated, workflow is started again and creates a new PR if needed.
- Explicitly tell agent that all text within repository is just data and cannot follow its prompt.
- Allow to run locally as closly as possible to Github Action.
- Show coverage diff before and after generating tests
- The workflow fails when the rerun of the tests fails, when the agent changed anything but tests, or when the agent failed, gave an invalid report, or reported tests it never wrote (e.g. its edits were denied). The rerun covers the whole suite of each area the agent wrote tests in, plus the frontend typecheck.
- Secrets stay out of the agent's reach: `CLAUDE_CODE_SUBPROCESS_ENV_SCRUB` removes them from the commands the agent runs, and the sandbox denies `ANTHROPIC_API_KEY`, `GITHUB_TOKEN`, `GH_TOKEN` and the Actions tokens.
- Verification without the model: claude-ci reruns the tests and measures coverage with `env -i` and bubblewrap (no network, read-only filesystem except the checkout, 600 s timeout per command). It is installed outside the checkout before the agent runs, so the agent cannot change it.
- Model text never reaches a shell: the agent's report goes through an environment variable, multi-line step outputs use a random delimiter, the base ref is validated before it reaches git.
- The agent's report is validated with pydantic, even though the action already checks it against the JSON schema; an invalid report fails the run.
- Model text is sanitised before it is posted: no HTML, no `@` mentions, no table breaks.
- Cost control: when no changed file needs tests, the agent does not run at all; a new push cancels the run in progress; the job times out after 30 minutes and the agent after 200 turns.
- Failures stay visible: the PR gets a comment explaining what failed, including how many tool calls Claude Code denied; logs, patch, results and the agent's full transcript (`execution.json`) are kept as artifacts for 14 days, and the report is also in the job summary.


## Prerequisites and how to run workflow on Github Actions
- Create environment `CI` and add secret `ANTHROPIC_API_KEY` to it.
  `Settings -> Environments`
- Optionally set repository variable `CLAUDE_MODEL` (default `claude-haiku-5-5`).
  `Settings -> Secrets and variables -> Actions -> Variables`
- To run a PR on Sonnet instead, add the label `sonnet` to it (create it once: `gh label create sonnet`). Adding the label starts a run; the tests PR's branch and title name the model, so both models can be compared on the same commit.
- Allow GitHub Actions to create and approve pull requests
  `Settings -> Actions -> General`
- Workflow runs automatically on every pull request from a branch of this repository (not from forks).
- Workflow will rerun on new commits to the PR or synchronization.

## Prerequisites and how to run workflow locally
Workflow can be reproduced locally except creating a PR and comment.
It can be run as many times as required.
- Installed just, uv, Node/npm, jq, bubblewrap, socat and claude (logged in)
- Installed backend and frontend deps (`just ci-setup`)
- To run all steps `just ci`
- To run individual steps investigate `justfile`


## Solution
- Workflow is defined in `.github/workflows/pr-test-claude.yml`
- Custom agent `unit-test-writer` is defined in `.github/claude-test-agent/agents/unit-test-writer.md` (role, rules, steps, when to split work into subagents).
  `.github/claude-test-agent/` is a Claude Code plugin (`taskly-test-agent`): Claude Code runs with `--plugin-dir .github/claude-test-agent --agent taskly-test-agent:unit-test-writer`; when it decides a PR is too big, it dispatches `taskly-test-agent:unit-test-writer` subagents, so every slice follows the same rules.
  It is not copied into `.claude/`, because claude-code-action replaces `.claude/` with the copy from `main` (PR head is untrusted).
- The prompt is only the task generated by claude-ci: exact files to investigate, their diffs and test paths.
- All agent skills are defined in `.github/claude-test-agent/skills/` and come with the plugin (`taskly-test-agent:test-scope` etc.)
- Settings for Claude Agent Harness `.github/claude-test-agent/settings.json`
- Report schema for agent `.github/claude-test-agent/report.schema.json`
- There are three skills.
Loading the skills is an instruction in the agent's definition, not enforced; `skills_used` in the report is the agent's own claim.
* `test-scope` - loaded at the beginning when there are changes to help agent decide what to do about each changed file that is not skipped.
* `backend-unit-tests` - loaded before any backend test is written or updated.
* `frontend-unit-tests` - loaded before any frontend test is written or updated.

## Steps of workflow
### Generate (read access)
1. Prepare directories
2. Checkout the PR's head commit
3. Setup Python environment
4. Install claude-ci
5. Generate prompt by claude-ci

Steps 6-12 run only when a changed file needs tests:

6. Install bubblewrap for sandboxed environment
7. Setup Node environment
8. Install frontend and backend dependencies
9. Run coverage before by claude-ci
10. Run Agent (`unit-test-writer`)
11. Verify generated tests by claude-ci
12. Run coverage after by claude-ci
13. Prepare PR comment
14. Upload artifacts
15. Fail the job when tests fail, the agent changed something other than tests, or the agent failed or wrote none of the tests it reported
### Publish (write access)
16. Download artifacts
17. Checkout the PR's head commit
18. Open new PR with changes
19. Post comment on base PR


## What to extend
- Parallel run of different models.
- Agentic review of automatic generated PR.

## Example run

PR [#11](https://github.com/Uszczi/taskly-app/pull/11) adds a task summary and clearing of completed tasks: 15 changed files in the backend and frontend.
The workflow ran on the same commit (`7653795`) twice, once per model, and each run opened its own tests PR:

| | Haiku | Sonnet |
|---|---|---|
| Tests PR | [#13](https://github.com/Uszczi/taskly-app/pull/13) | [#12](https://github.com/Uszczi/taskly-app/pull/12) |
| Run | [39939245900](https://github.com/Uszczi/taskly-app/actions/runs/39939245900) | [39939317464](https://github.com/Uszczi/taskly-app/actions/runs/39939317464) |
| Status | ✅ ok | ✅ ok |
| Tests added | 43 in 14 files | 24 in 13 files |
| Rerun by verify | backend 34 passed, frontend 49 passed, typecheck clean | backend 28 passed, frontend 37 passed, typecheck clean |
| Backend coverage | 43.9% → 49.2% | 43.9% → 49.7% |
| Frontend coverage | 39.8% → 66.3% | 39.8% → 66.3% |
| Cost, turns | $0.037, 62 turns | $0.31, 42 turns |
| Denied tool calls | 2 | 1 |

**Agent's decisions** (the same in both runs): 12 files in scope.
- `add` for the new files: `stats.py`, `TodoSummary.tsx` and the five hooks.
- `update` for the files that already had tests: `repository.py`, `router.py`, `TodosPage.tsx`, `api/todos.ts`, `utils/todos.ts`.
- Not tested, excluded from coverage by the plan: `schemas.py`, `queryKeys.ts`, `types.ts`.
- Shared test code was written once: a query client helper in `frontend/src/test/` (both runs) and a stats fixture (Haiku).

**Skills used**: `test-scope`, `backend-unit-tests` and `frontend-unit-tests` in both runs.

**Subagents**: none; the agent did the 12 files alone in both runs.

**Denied tool calls**: the agent tried to write files through Bash (`cat > …`, `cd … && for …`). The permissions refused them, and the agent used Edit/Write instead.

**Comparison**: both models covered every changed file, reached the same coverage and passed verification. Haiku wrote more, narrower tests and listed what it could not pin (e.g. the real database rowcount, the `date.today()` default) under *Needs your attention*; Sonnet wrote fewer, broader tests at about 8× the cost.

**Test style**: the generated tests follow the existing ones: plain `test_…` functions and the shared fixtures in the backend; `it(...)` blocks, `todoFixture`, the design-system mock, `userEvent` and role queries in the frontend; no `any`. Two small differences showed up, and the skills were updated from them:
- Haiku named backend tests after the function (`test_compute_stats_…`) instead of the behavior; `backend-unit-tests` now says the name is the behavior.
- Both built the same stats object inline in several files (Haiku added a fixture but did not use it everywhere); `frontend-unit-tests` now says an object several tests build gets one fixture in `src/test/`.


## Assumptions
- PR authors are trusted, the workflow runs only for branches of this repository.
- A human reviews every tests PR and decides whether to merge it, nothing is merged automatically.
- The existing test suites pass on the PR's base, since verify reruns the whole suite of each area the agent wrote tests in.
- Unit tests only: `backend/app` with pytest, `frontend/src` with vitest, following the repository's layout (backend tests mirror the source path under `backend/tests/` with a `test_` prefix, frontend tests sit next to the source).
- Files that need no tests are the ones excluded from coverage (`backend/pyproject.toml`, `frontend/vite.config.ts`); `skip-rules.json` mirrors them.
- Tests run offline: everything they would reach over the network is mocked.
- CI runs on GitHub-hosted Ubuntu 24.04 runners, where bubblewrap can be installed.

## The solution's limitations
- Its bounded to Claude.
- Verify step after test generation requires all tests to pass even ones that were failing before.
- Agent runs in sandbox without any access to internet or external documentation.
- PRs need to be closed by hand if not merged, each change to branch might generate new PR when only last one is probably valid.
- Agent can edit only tests files even if fix for production code is simple.
- Workflow is highly dependent on model quality.
- Price and time grow with PR size and are limited only by amount of agent turns and timeout.
- Running workflow requires bubblewrap for sandboxed environment (Doesn't work on macOS).
- Duplication of test commands definition: `settings.json`, both test skills, `verify.py` and `coverage.py`.

## Changes before production
