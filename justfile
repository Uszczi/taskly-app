# Runs the steps of .github/workflows/pr-test-claude.yml locally, on the branch checked out here.
# Needs uv, jq, bubblewrap, socat and claude (logged in); `just ci-setup` installs the rest.

set shell := ["bash", "-euo", "pipefail", "-c"]
set quiet

out := env("CI_OUT", "/tmp/taskly-claude-ci")
base := env("CI_BASE", "main")
model := env("CLAUDE_MODEL", "claude-haiku-5-5")
cli := "uv run -q --project claude-ci taskly-claude-ci --out " + out

# Every step, as the workflow runs them
ci: ci-clean ci-plan ci-coverage-before ci-claude ci-verify ci-coverage-after ci-comment

ci-setup:
    uv venv backend/.venv --python 3.12 --allow-existing
    uv pip install --python backend/.venv -r backend/requirements.txt
    npm ci --prefix frontend

# claude-ci's own tests and type check
ci-test:
    cd claude-ci && uv run pytest -q && uv run --with mypy mypy --strict src

ci-clean:
    rm -rf {{out}}

ci-plan:
    mkdir -p {{out}}
    {{cli}} prompt --base {{base}} \
      --schema .github/claude-test-agent/report.schema.json | head -n 1
    jq -r '.targets[] | "\(.source) -> \(.test)\(if .test_exists then "" else " (new)" end)"' {{out}}/plan.json

ci-coverage-before:
    {{cli}} coverage before --base {{base}}

ci-claude:
    #!/usr/bin/env bash
    set -euo pipefail
    test -f {{out}}/prompt.md || { echo "nothing to test"; exit 0; }
    if [ -n "$(git status --porcelain)" ]; then
      echo "commit or stash your changes first: verify must see only what Claude writes"; exit 1
    fi
    CLAUDE_CODE_SUBPROCESS_ENV_SCRUB=1 claude -p "$(cat {{out}}/prompt.md)" \
      --setting-sources project \
      --plugin-dir .github/claude-test-agent \
      --agent taskly-test-agent:unit-test-writer \
      --settings .github/claude-test-agent/settings.json \
      --model {{model}} --max-turns 200 \
      --json-schema "$(jq -c . .github/claude-test-agent/report.schema.json)" \
      --output-format stream-json --verbose > {{out}}/claude.jsonl
    jq -s . {{out}}/claude.jsonl > {{out}}/execution.json

ci-verify:
    #!/usr/bin/env bash
    set -euo pipefail
    result=$(jq -c 'select(.type == "result")' {{out}}/claude.jsonl | tail -n 1)
    conclusion=$(jq -r 'if .is_error then "failure" else "success" end' <<< "$result")
    git add -A
    if ! git diff --cached --quiet; then git diff --cached --binary > {{out}}/tests.patch; fi
    git reset -q
    REPORT=$(jq -c '.structured_output // empty' <<< "$result") {{cli}} verify --conclusion "$conclusion"

ci-coverage-after:
    {{cli}} coverage after --base {{base}}

ci-comment:
    {{cli}} comment --run-url "local run" --model {{model}} --execution-file {{out}}/execution.json

[confirm("Delete the test files Claude wrote (listed in result.json)?")]
ci-reset:
    #!/usr/bin/env bash
    set -euo pipefail
    jq -r '.written[]' {{out}}/result.json | while IFS= read -r path; do
      if git cat-file -e "HEAD:$path" 2>/dev/null; then git checkout -q HEAD -- "$path"; else rm -f -- "$path"; fi
      echo "reset $path"
    done
