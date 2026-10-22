import re

from .models import Coverage, ExecutionEntry, Plan, Result, Status

MARKER = "<!-- taskly-test-agent:claude -->"

_STATUS: dict[Status, str] = {
    "tests_failed": "❌ Generated tests fail; no PR opened",
    "violation": "❌ Claude changed files that are not tests; no PR opened",
    "agent_failed": "❌ Claude Code failed or gave no report",
    "nothing_to_test": "✅ No changed source file needs unit tests",
}
_FILE = re.compile(r"^diff --git a/.+ b/(.+)$")
_JS_TEST = re.compile(
    r"""^(?P<sign>[+-])\s*(?:it|test)(?:\.\w+)?\(\s*(?P<q>['"`])(?P<name>.+?)(?P=q)"""
)
_PY_TEST = re.compile(r"^(?P<sign>[+-])\s*(?:async\s+)?def\s+test_(?P<name>\w+)\s*\(")


def safe(text: str) -> str:
    text = re.sub(r"[<>]", "", text)  # no raw HTML, no fake MARKER
    text = text.replace("@", "@\u200b")  # no mentions of people or teams
    return text.replace("|", "\\|").replace("\n", " ")


def added_tests(patch: str) -> dict[str, list[str]]:
    added: dict[str, list[str]] = {}
    removed: dict[str, set[str]] = {}
    path: str | None = None
    for line in patch.splitlines():
        if file := _FILE.match(line):
            path = file.group(1)
        elif path and (test := _JS_TEST.match(line) or _PY_TEST.match(line)):
            name = (
                test["name"].replace("_", " ") if test.re is _PY_TEST else test["name"]
            )
            if test["sign"] == "+":
                added.setdefault(path, []).append(name)
            else:
                removed.setdefault(path, set()).add(name)
    kept = {
        p: [n for n in names if n not in removed.get(p, set())]
        for p, names in added.items()
    }
    return {p: names for p, names in kept.items() if names}


def coverage_table(before: Coverage, after: Coverage) -> list[str]:

    def pct(value: float | None) -> str:
        return "–" if value is None else f"{round(value, 1):g}%"

    def change(old: float | None, new: float | None) -> str:
        if old is None or new is None:
            return ""
        delta = round(new - old, 1)
        return f"{delta:+g}" if delta else "0"

    def row(name: str, old: float | None, new: float | None) -> str:
        return f"| {name} | {pct(old)} | {pct(new)} | {change(old, new)} |"

    rows: list[str] = []
    for area, old, new in (
        ("backend", before.backend, after.backend),
        ("frontend", before.frontend, after.frontend),
    ):
        if not old and not new:
            continue
        old_files = old.files if old else {}
        new_files = new.files if new else {}
        for path in sorted(old_files.keys() | new_files.keys()):
            rows.append(
                row(f"`{safe(path)}`", old_files.get(path), new_files.get(path))
            )
        rows.append(
            row(
                f"**{area} total**",
                old.total if old else None,
                new.total if new else None,
            )
        )
    return (
        [
            "**Coverage**",
            "",
            "| File | Before | After | Change |",
            "|---|---|---|---|",
            *rows,
        ]
        if rows
        else []
    )


def usage_footer(entries: list[ExecutionEntry], model: str) -> str:
    results = [e for e in entries if e.type == "result"]
    if not results:
        return model
    cost, turns = results[-1].total_cost_usd, results[-1].num_turns
    parts = [
        model,
        f"${cost:.4f}" if cost is not None else None,
        f"{turns} turns" if turns is not None else None,
    ]
    return " · ".join(p for p in parts if p)


def render(
    result: Result | None,
    plan: Plan,
    patch: str,
    before: Coverage,
    after: Coverage,
    run_url: str,
    footer: str,
) -> str:
    tests = added_tests(patch)
    count = sum(len(names) for names in tests.values())

    if result is None:
        status = "❌ The run failed before Claude's work was verified"
    elif result.status == "ok":
        status = (
            f"✅ {count} test{'s' if count != 1 else ''} added, passing"
            if count
            else "✅ No new tests needed"
        )
    else:
        status = _STATUS[result.status]
    lines = [
        MARKER,
        f"## 🧪 Test agent (Claude Code): {status}",
        "",
        f"[run log]({run_url})",
        "",
    ]

    report = result.report if result else None
    if report and (summary := safe(report.summary).strip()):
        lines += [f"> {summary}", ""]

    if tests:
        lines += [
            "**Now covered**"
            if result and result.status == "ok"
            else "**Written, not proposed**",
            "",
        ]
        for path, names in tests.items():
            lines += [f"- `{safe(path)}`", *[f"  - {safe(name)}" for name in names]]
        lines.append("")

    if table := coverage_table(before, after):
        lines += [*table, ""]

    untested = {s.path: s.reason for s in plan.skipped if s.excluded}
    for decision in report.decisions if report else []:
        if decision.action == "skip":
            untested.setdefault(safe(decision.path), safe(decision.reason))
    if untested:
        lines += ["**Changed files without tests**", "", "| File | Why |", "|---|---|"]
        lines += [f"| `{path}` | {reason} |" for path, reason in untested.items()] + [
            ""
        ]

    attention: list[str] = []
    if result is None:
        attention.append("No verification result; see the run log.")
    else:
        for run in result.runs:
            if run.exit_code != 0:
                what = (
                    "Frontend typecheck (`tsc --noEmit`)"
                    if run.target == "typecheck"
                    else f"{run.target} tests"
                )
                attention.append(
                    f"{what} fails when rerun without the model; see {run.target}.log in the run artifacts."
                )
        attention += [
            f"`{safe(p)}` is not a test file; no PR was opened."
            for p in result.violations
        ]
        attention += [safe(item) for item in report.attention] if report else []
    if attention:
        lines += [
            "**Needs your attention**",
            "",
            *[f"- {item}" for item in attention],
            "",
        ]

    if footer:
        lines.append(f"<sub>{footer}</sub>")
    return "\n".join(lines).rstrip("\n")
