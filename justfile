# Run the Claude Code test workflow (.github/workflows/pr-test-claude.yml) locally,
# step by step or all at once, on the branch checked out here.
#
#   just ci            # every step, against main
#   just ci-plan       # one step; see `just --list`
#
# Needs: uv, jq, claude (logged in), bubblewrap and socat for the sandboxes,
# backend/.venv and frontend/node_modules installed.

set shell := ["bash", "-euo", "pipefail", "-c"]

# Outside the checkout, like $RUNNER_TEMP in CI: verify treats any new file in it as a violation.
out := env("CI_OUT", "/tmp/taskly-claude-ci")
base := env("CI_BASE", "main")
model := env("CLAUDE_MODEL", "claude-haiku-5-5")
cli := "uv run -q --project claude-ci taskly-claude-ci --out " + out

# Every step, as the workflow runs them.
ci: ci-clean ci-plan ci-coverage-before ci-claude ci-verify ci-coverage-after ci-comment

# claude-ci's own tests and type check (no model, no network).
ci-test:
    cd claude-ci && uv run pytest -q && uvx mypy --strict src

# Start over: remove the out directory.
ci-clean:
    rm -rf {{out}}

# Step 1: plan.json and Claude's prompt.md for the changes since `base`.
ci-plan:
    mkdir -p {{out}}
    {{cli}} prompt --base {{base}} \
      --instructions agent-shared/instructions.md \
      --instructions .github/claude-test-agent/prompt.md
    jq -r '"targets: \(.targets | length)  skipped: \(.skipped | length)", (.targets[] | "  \(.source) -> \(.test)\(if .test_exists then "" else " (new)" end)")' {{out}}/plan.json

# Step 2: coverage of the changed areas before any new test.
ci-coverage-before:
    agent-shared/coverage.sh measure {{base}} {{out}}/coverage-before.json
    jq -c 'map_values(.total)' {{out}}/coverage-before.json

# Step 3: Claude Code with CI's settings, sandbox and skills (uses your Claude Code login).
ci-claude:
    #!/usr/bin/env bash
    set -euo pipefail
    test -f {{out}}/prompt.md || { echo "nothing to test (see plan.json)"; exit 0; }
    command -v bwrap socat > /dev/null || { echo "install bubblewrap and socat first"; exit 1; }
    # CI gives Claude the test skills in place of the developers' ones; put those back after.
    trap 'rm -rf .claude/skills && git checkout -q -- .claude' EXIT
    rm -rf .claude/skills && mkdir -p .claude/skills && cp -r agent-shared/skills/. .claude/skills/
    # --setting-sources project: none of your user settings, hooks or permissions (CI has none).
    CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1 claude -p "$(cat {{out}}/prompt.md)" \
      --setting-sources project \
      --settings .github/claude-test-agent/settings.json \
      --model {{model}} --max-turns 200 \
      --json-schema "$(jq -c . agent-shared/report.schema.json)" \
      --output-format stream-json --verbose > {{out}}/claude.jsonl
    # The action's execution file: the same messages as one JSON array.
    jq -s . {{out}}/claude.jsonl > {{out}}/execution.json
    jq -c 'select(.type == "result") | {subtype, is_error, num_turns, total_cost_usd}' {{out}}/claude.jsonl

# Step 4: check what Claude changed and rerun its tests; writes result.json and tests.patch.
ci-verify:
    #!/usr/bin/env bash
    set -euo pipefail
    test -f {{out}}/claude.jsonl || { echo "run ci-claude first"; exit 1; }
    result=$(jq -c 'select(.type == "result")' {{out}}/claude.jsonl | tail -n 1)
    conclusion=$(jq -r 'if .is_error then "failure" else "success" end' <<< "$result")
    # Like the workflow, the report reaches verify through the environment only.
    REPORT=$(jq -c '.structured_output // empty' <<< "$result") {{cli}} verify --conclusion "$conclusion"
    jq '{status, written, violations, runs}' {{out}}/result.json
    # verify stages the written tests to build the patch; leave them unstaged here.
    git reset -q

# Step 5: coverage after Claude's tests, and the comment's coverage table.
ci-coverage-after:
    agent-shared/coverage.sh measure {{base}} {{out}}/coverage-after.json
    agent-shared/coverage.sh render {{base}} {{out}}/coverage-before.json {{out}}/coverage-after.json > {{out}}/coverage.md
    cat {{out}}/coverage.md

# Step 6: the PR comment, as publish would post it.
ci-comment:
    {{cli}} comment --run-url "local run" --model {{model}} \
      $(test -f {{out}}/execution.json && echo --execution-file {{out}}/execution.json) > {{out}}/comment.md
    cat {{out}}/comment.md

# Throw away what Claude wrote in this checkout (tracked changes and new test files).
ci-reset:
    git checkout -q -- backend/tests frontend/src
    git clean -fdq -- backend/tests frontend/src
