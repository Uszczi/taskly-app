"""The report: which behaviors the new tests pin and what still needs a human.

It is the body of the pull request that proposes the tests, or the comment on
the source pull request when no tests are proposed.

Test names come from the patch, not from Claude's report. Report text and test
names come from a model that read the PR's code, so they are untrusted:
HTML and mentions are neutralised before they reach GitHub.
"""

import json
import re
from pathlib import Path

from .models import Plan, Result, Status

MARKER = "<!-- taskly-test-agent:claude -->"
# In the tests PR's body, the publish job replaces this with a link to the source PR.
LINK_SLOT = "<!-- link -->"

_STATUS: dict[Status, str] = {
    "tests_failed": "❌ Generated tests fail; no PR opened",
    "violation": "❌ Claude changed files that are not tests; no PR opened",
    "agent_failed": "❌ Claude Code failed or gave no report",
    "nothing_to_test": "✅ No changed source file needs unit tests",
}
_FILE = re.compile(r"^diff --git a/.+ b/(.+)$")
_JS_TEST = re.compile(r"""^(?P<sign>[+-])\s*(?:it|test)(?:\.\w+)?\(\s*(?P<q>['"`])(?P<name>.+?)(?P=q)""")
_PY_TEST = re.compile(r"^(?P<sign>[+-])\s*(?:async\s+)?def\s+test_(?P<name>\w+)\s*\(")


def safe(text: str) -> str:
    text = re.sub(r"[<>]", "", text)  # no raw HTML, no fake MARKER or LINK_SLOT
    text = text.replace("@", "@\u200b")  # no mentions of people or teams
    return text.replace("|", "\\|").replace("\n", " ")


def added_tests(patch: str) -> dict[str, list[str]]:
    """Names of the tests a patch adds, per file. A name it also removes was moved, not added."""
    added: dict[str, list[str]] = {}
    removed: dict[str, set[str]] = {}
    path: str | None = None
    for line in patch.splitlines():
        if file := _FILE.match(line):
            path = file.group(1)
        elif path and (test := _JS_TEST.match(line) or _PY_TEST.match(line)):
            name = test["name"].replace("_", " ") if test.re is _PY_TEST else test["name"]
            if test["sign"] == "+":
                added.setdefault(path, []).append(name)
            else:
                removed.setdefault(path, set()).add(name)
    kept = {p: [n for n in names if n not in removed.get(p, set())] for p, names in added.items()}
    return {p: names for p, names in kept.items() if names}


def usage_footer(execution_file: Path | None, model: str) -> str:
    """Model, cost and turns from claude-code-action's execution file."""
    try:
        entries: object = json.loads(execution_file.read_text()) if execution_file else []
    except (OSError, ValueError):
        entries = []
    if not isinstance(entries, list):
        entries = []
    results = [e for e in entries if isinstance(e, dict) and e.get("type") == "result"]
    if not results:
        return model
    cost, turns = results[-1].get("total_cost_usd"), results[-1].get("num_turns")
    parts = [model, f"${cost:.4f}" if cost is not None else None, f"{turns} turns" if turns is not None else None]
    return " · ".join(p for p in parts if p)


def render(out: Path, run_url: str, footer: str) -> str:
    def read(name: str) -> str:
        path = out / name
        return path.read_text() if path.exists() else ""

    result: Result | None
    try:
        result = json.loads(read("result.json"))
    except ValueError:
        result = None
    plan: Plan = json.loads(read("plan.json") or '{"targets": [], "skipped": [], "changed_tests": []}')
    tests = added_tests(read("tests.patch"))
    count = sum(len(names) for names in tests.values())

    if result is None:
        status = "❌ The run failed before Claude's work was verified"
    elif result["status"] == "ok":
        status = f"✅ {count} test{'s' if count != 1 else ''} added, passing" if count else "✅ No new tests needed"
    else:
        status = _STATUS[result["status"]]
    lines = [MARKER, f"## 🧪 Test agent (Claude Code): {status}", "", f"[run log]({run_url}){LINK_SLOT}", ""]

    report = (result.get("report") if result else None) or {}
    if summary := safe(str(report.get("summary", ""))).strip():
        lines += [f"> {summary}", ""]

    if tests:
        lines += ["**Now covered**" if result and result["status"] == "ok" else "**Written, not proposed**", ""]
        for path, names in tests.items():
            lines += [f"- `{safe(path)}`", *[f"  - {safe(name)}" for name in names]]
        lines.append("")

    # Written by .github/claude-test-agent/coverage.sh from the coverage reports; no model text.
    if coverage := read("coverage.md").strip():
        lines += [coverage, ""]

    untested = {s["path"]: s["reason"] for s in plan["skipped"] if s["excluded"]}
    for decision in report.get("decisions", []):
        if decision.get("action") == "skip":
            untested.setdefault(safe(str(decision.get("path"))), safe(str(decision.get("reason"))))
    if untested:
        lines += ["**Changed files without tests**", "", "| File | Why |", "|---|---|"]
        lines += [f"| `{path}` | {reason} |" for path, reason in untested.items()] + [""]

    attention: list[str] = []
    if result is None:
        attention.append("No verification result; see the run log.")
    else:
        for run in result.get("runs", []):
            if run["exit_code"] != 0:
                what = "Frontend typecheck (`tsc --noEmit`)" if run["target"] == "typecheck" else f"{run['target']} tests"
                attention.append(f"{what} fails when rerun without the model; see {run['target']}.log in the run artifacts.")
        attention += [f"`{safe(p)}` is not a test file; no PR was opened." for p in result.get("violations", [])]
        attention += [safe(str(item)) for item in report.get("attention", [])]
    if attention:
        lines += ["**Needs your attention**", "", *[f"- {item}" for item in attention], ""]

    if footer:
        lines.append(f"<sub>{footer}</sub>")
    return "\n".join(lines).rstrip("\n") + "\n"
