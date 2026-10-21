"""Render the agent's JSON result as the pull request comment.

Runs in the unprivileged CI job; the privileged job only posts the text.
The comment answers what a reviewer needs: which behaviors the new tests pin,
and what still needs a human. The tests come from the patch, not from the
model's report. Report text and test names come from a model that read the
PR's code, so they are untrusted: mentions and HTML are neutralised before
they reach GitHub.
"""

import argparse
import json
import re
from pathlib import Path

from .errors import ExitCode

MARKER = "<!-- taskly-test-agent -->"
# The publish job replaces this with a link to the commit it pushed.
COMMIT_SLOT = "<!-- commit -->"

_STATUS = {
    ExitCode.CONFIG: "⚠️ Configuration error",
    ExitCode.PROVIDER_TRANSIENT: "⚠️ Model provider unavailable (retries exhausted)",
    ExitCode.PROVIDER_FATAL: "❌ Model provider error",
    ExitCode.AGENT_FAILED: "❌ Agent failed",
    ExitCode.TESTS_FAILED: "❌ Generated tests fail or were not run; not committed",
}

_FILE = re.compile(r"^diff --git a/.+ b/(.+)$")
_JS_TEST = re.compile(r"""^\+\s*(?:it|test)(?:\.\w+)?\(\s*(['"`])(.+?)\1""")
_PY_TEST = re.compile(r"^\+\s*(?:async\s+)?def\s+test_(\w+)\s*\(")


def _safe(text: str) -> str:
    text = re.sub(r"[<>]", "", text)  # no raw HTML, no fake MARKER or COMMIT_SLOT
    text = text.replace("@", "@\u200b")  # no mentions of people or teams
    return text.replace("|", "\\|").replace("\n", " ")


def added_tests(patch: str) -> dict[str, list[str]]:
    """Names of the tests a patch adds, per test file, in patch order."""
    tests: dict[str, list[str]] = {}
    path = None
    for line in patch.splitlines():
        if match := _FILE.match(line):
            path = match.group(1)
        elif path and (match := _JS_TEST.match(line)):
            tests.setdefault(path, []).append(match.group(2))
        elif path and (match := _PY_TEST.match(line)):
            tests.setdefault(path, []).append(match.group(1).replace("_", " "))
    return tests


def _footer(usage: str) -> str:
    model = re.search(r"── usage: (.+?) ──", usage)
    cost = re.search(r"^cost:\s+(\S+)", usage, re.M)
    requests = re.search(r"^requests:\s+(\d+)", usage, re.M)
    parts = [
        model.group(1) if model else None,
        cost.group(1) if cost else None,
        f"{requests.group(1)} requests" if requests else None,
    ]
    return " · ".join(p for p in parts if p)


def render(result: dict | None, exit_code: int, usage: str, run_url: str, patch: str = "") -> str:
    tests = added_tests(patch)
    count = sum(len(names) for names in tests.values())
    if exit_code == ExitCode.OK:
        if result is not None and not result.get("agent_ran"):
            status = "✅ No changed source file needs unit tests"
        elif count:
            status = f"✅ {count} test{'s' if count != 1 else ''} added, passing"
        else:
            status = "✅ No new tests needed"
    else:
        status = _STATUS.get(exit_code, f"❌ Agent crashed (exit code {exit_code})")
    lines = [MARKER, f"## 🧪 Test agent: {status}", "", f"[run log]({run_url}){COMMIT_SLOT}", ""]

    if tests:
        title = "Now covered" if exit_code == ExitCode.OK else "Written, not committed"
        lines += [f"**{title}**", ""]
        for path, names in tests.items():
            lines.append(f"- `{_safe(Path(path).name)}`")
            lines += [f"  - {_safe(name)}" for name in names]
        lines.append("")

    # Changed source code left without tests, by the coverage rules or by the model's
    # call: the reviewer checks it by eye.
    untested: dict[str, str] = {}
    if result is not None:
        if plan := result.get("plan"):
            untested |= {s["path"]: s["reason"] for s in plan["skipped"] if s.get("excluded")}
        if report := result.get("report"):
            for d in report.get("decisions", []):
                if d["action"] == "skip":
                    untested.setdefault(_safe(d["path"]), _safe(d["reason"]))
    if untested:
        lines += ["**Changed files without tests**", "", "| File | Why |", "|---|---|"]
        lines += [f"| `{path}` | {reason} |" for path, reason in untested.items()]
        lines.append("")

    attention: list[str] = []
    if result is None:
        attention.append("The agent produced no result; see the run log.")
    else:
        if error := result.get("error"):
            attention.append(f"Error `{error['kind']}`: {_safe(error['message'])}")
        # Recorded by the tools, not claimed by the model.
        attention += [f"`{p}` fails or was never run." for p in result.get("unverified_tests") or []]
        if report := result.get("report"):
            attention += [_safe(item) for item in report.get("attention", [])]
    if attention:
        lines += ["**Needs your attention**", "", *[f"- {item}" for item in attention], ""]

    if footer := _footer(usage):
        lines.append(f"<sub>{footer}</sub>")
    return "\n".join(lines).rstrip("\n") + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskly-pr-comment")
    parser.add_argument("--result", type=Path, required=True, help="agent stdout (JSON)")
    parser.add_argument("--stderr", type=Path, required=True, help="agent stderr")
    parser.add_argument("--patch", type=Path, help="the test patch the run produced")
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()

    try:
        result = json.loads(args.result.read_text())
    except (OSError, ValueError):
        result = None
    stderr = args.stderr.read_text() if args.stderr.exists() else ""
    usage = stderr[stderr.find("── usage:"):] if "── usage:" in stderr else ""
    patch = args.patch.read_text() if args.patch and args.patch.exists() else ""
    print(render(result, args.exit_code, usage, args.run_url, patch), end="")
