"""The PR comment: which behaviors the new tests pin and what still needs a human.

Test names come from the patch, not from Claude's report. Report text and test
names come from a model that read the PR's code, so they are untrusted:
HTML and mentions are neutralised before they reach GitHub.
"""

import json
import re
from pathlib import Path

MARKER = "<!-- taskly-test-agent:claude -->"
# The publish job replaces this with a link to the commit it pushed.
COMMIT_SLOT = "<!-- commit -->"

_STATUS = {
    "tests_failed": "❌ Generated tests fail; not committed",
    "violation": "❌ Claude changed files that are not tests; not committed",
    "agent_failed": "❌ Claude Code failed or gave no report",
    "nothing_to_test": "✅ No changed source file needs unit tests",
}
_FILE = re.compile(r"^diff --git a/.+ b/(.+)$")
_JS_TEST = re.compile(r"""^([+-])\s*(?:it|test)(?:\.\w+)?\(\s*(['"`])(.+?)\2""")
_PY_TEST = re.compile(r"^([+-])\s*(?:async\s+)?def\s+test_(\w+)\s*\(")


def safe(text: str) -> str:
    text = re.sub(r"[<>]", "", text)  # no raw HTML, no fake MARKER or COMMIT_SLOT
    text = text.replace("@", "@\u200b")  # no mentions of people or teams
    return text.replace("|", "\\|").replace("\n", " ")


def added_tests(patch: str) -> dict[str, list[str]]:
    """Names of the tests a patch adds, per file. A name it also removes was moved, not added."""
    added: dict[str, list[str]] = {}
    removed: dict[str, set[str]] = {}
    path = None
    for line in patch.splitlines():
        if match := _FILE.match(line):
            path = match.group(1)
        elif path and (match := _JS_TEST.match(line) or _PY_TEST.match(line)):
            sign, name = match.group(1), match.group(match.lastindex)
            if match.re is _PY_TEST:
                name = name.replace("_", " ")
            if sign == "+":
                added.setdefault(path, []).append(name)
            else:
                removed.setdefault(path, set()).add(name)
    kept = {p: [n for n in names if n not in removed.get(p, set())] for p, names in added.items()}
    return {p: names for p, names in kept.items() if names}


def usage_footer(execution_file: Path | None, model: str) -> str:
    """Model, cost and turns from claude-code-action's execution file."""
    try:
        entries = json.loads(execution_file.read_text()) if execution_file else []
    except (OSError, ValueError):
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

    try:
        result = json.loads(read("result.json"))
    except ValueError:
        result = None
    plan = json.loads(read("plan.json") or "{}")
    tests = added_tests(read("tests.patch"))
    count = sum(len(names) for names in tests.values())

    if result is None:
        status = "❌ The run failed before Claude's work was verified"
    elif result["status"] == "ok":
        status = f"✅ {count} test{'s' if count != 1 else ''} added, passing" if count else "✅ No new tests needed"
    else:
        status = _STATUS[result["status"]]
    lines = [MARKER, f"## 🧪 Test agent (Claude Code): {status}", "", f"[run log]({run_url}){COMMIT_SLOT}", ""]

    if tests:
        lines += ["**Now covered**" if result and result["status"] == "ok" else "**Written, not committed**", ""]
        for path, names in tests.items():
            lines += [f"- `{safe(path)}`", *[f"  - {safe(name)}" for name in names]]
        lines.append("")

    # Written by agent-shared/coverage.sh from the coverage reports; no model text.
    if coverage := read("coverage.md").strip():
        lines += [coverage, ""]

    report = (result or {}).get("report") or {}
    untested = {s["path"]: s["reason"] for s in plan.get("skipped", []) if s.get("excluded")}
    for decision in report.get("decisions", []):
        if decision.get("action") == "skip":
            untested.setdefault(safe(str(decision.get("path"))), safe(str(decision.get("reason"))))
    if untested:
        lines += ["**Changed files without tests**", "", "| File | Why |", "|---|---|"]
        lines += [f"| `{path}` | {reason} |" for path, reason in untested.items()] + [""]

    attention = []
    if result is None:
        attention.append("No verification result; see the run log.")
    else:
        for run in result.get("runs", []):
            if run["exit_code"] != 0:
                what = "Frontend typecheck (`tsc --noEmit`)" if run["target"] == "typecheck" else f"{run['target']} tests"
                attention.append(f"{what} fails when rerun without the model; see {run['target']}.log in the run artifacts.")
        attention += [f"`{safe(p)}` is not a test file; nothing was committed." for p in result.get("violations", [])]
        attention += [safe(str(item)) for item in report.get("attention", [])]
    if attention:
        lines += ["**Needs your attention**", "", *[f"- {item}" for item in attention], ""]

    if footer:
        lines.append(f"<sub>{footer}</sub>")
    return "\n".join(lines).rstrip("\n") + "\n"
