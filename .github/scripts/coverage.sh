#!/usr/bin/env bash
# Coverage before and after the test agent, for the PR comment. No model involved.
#
#   coverage.sh measure BASE_SHA OUT.json
#       Runs the full test suite of each area the PR changes (backend, frontend)
#       with coverage, sandboxed like the Verify step: empty environment, no
#       network, read-only filesystem except the checkout. Failing tests still
#       produce a report. Writes {area: {total, files: {path: percent}}}.
#   coverage.sh render BASE_SHA BEFORE.json AFTER.json
#       Prints the comment section: every changed source file that has
#       coverage, plus each area's total.
#
# Coverage counts what backend/pyproject.toml and frontend/vite.config.ts
# include, so excluded files never show up. Run from the repository root.
set -euo pipefail

changed() {
  git diff --name-only --diff-filter=AMR "$1...HEAD" -- backend/app frontend/src
}

sandboxed() {
  local dir=$1; shift
  env -i PATH="$PATH" HOME="$HOME" NO_COLOR=1 CI=1 PYTHONDONTWRITEBYTECODE=1 \
    bwrap --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --bind "$PWD" "$PWD" \
      --unshare-all --die-with-parent --chdir "$dir" -- "$@"
}

measure() {
  local base=$1 out=$2 result='{}' files
  files=$(changed "$base")

  if grep -q '^backend/' <<< "$files"; then
    rm -rf backend/coverage
    sandboxed "$PWD/backend" .venv/bin/python -m pytest -q -p no:cacheprovider \
      --cov --cov-report=json:coverage/coverage.json > /dev/null 2>&1 || true
    if [ -f backend/coverage/coverage.json ]; then
      result=$(jq -c --argjson r "$result" '$r + {backend: {
          total: .totals.percent_covered,
          files: (.files | with_entries({key: "backend/\(.key)", value: .value.summary.percent_covered}))}}' \
        backend/coverage/coverage.json)
    fi
    rm -rf backend/coverage backend/.coverage
  fi

  if grep -q '^frontend/' <<< "$files"; then
    rm -rf frontend/coverage
    sandboxed "$PWD/frontend" node_modules/.bin/vitest run --coverage \
      --coverage.reporter=json-summary --coverage.reportOnFailure > /dev/null 2>&1 || true
    if [ -f frontend/coverage/coverage-summary.json ]; then
      result=$(jq -c --argjson r "$result" --arg root "$PWD/" '$r + {frontend: {
          total: .total.lines.pct,
          files: (del(.total) | with_entries({key: (.key | ltrimstr($root)), value: .value.lines.pct}))}}' \
        frontend/coverage/coverage-summary.json)
    fi
    rm -rf frontend/coverage
  fi

  echo "$result" > "$out"
}

render() {
  local base=$1 before=$2 after=$3
  # A missing measurement (its step failed) counts as no coverage data.
  changed "$base" | jq -rRn --slurpfile b <(cat "$before" 2>/dev/null || echo '{}') \
    --slurpfile a <(cat "$after" 2>/dev/null || echo '{}') '
    # Paths come from the PR: no HTML, no mentions, no table breaks.
    def safe: gsub("[<>]"; "") | gsub("@"; "@​") | gsub("\\|"; "\\|");
    def pct: if . == null then "–" else "\((. * 10 | round) / 10)%" end;
    def delta($x; $y):
      if $x == null or $y == null then ""
      else (($y - $x) * 10 | round / 10) as $d
        | if $d > 0 then "+\($d)" elif $d < 0 then "\($d)" else "0" end end;
    def row($name; $x; $y): "| \($name) | \($x | pct) | \($y | pct) | \(delta($x; $y)) |";
    $b[0] as $b | $a[0] as $a | [inputs] as $changed
    | [("backend", "frontend") as $area | select($a[$area] or $b[$area])
        | ([$changed[] | select(startswith($area + "/"))
              | select($a[$area].files[.] != null or $b[$area].files[.] != null)
              | row("`\(safe)`"; $b[$area].files[.]; $a[$area].files[.])]
           + [row("**\($area) total**"; $b[$area].total; $a[$area].total)])[]] as $rows
    | if ($rows | length) == 0 then empty
      else (["**Coverage**", "", "| File | Before | After | Change |", "|---|---|---|---|"] + $rows)
        | join("\n") end'
}

case ${1:-} in
  measure) measure "$2" "$3" ;;
  render) render "$2" "$3" "$4" ;;
  *) echo "usage: $0 measure BASE OUT.json | render BASE BEFORE.json AFTER.json" >&2; exit 2 ;;
esac
