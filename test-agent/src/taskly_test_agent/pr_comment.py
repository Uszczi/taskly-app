"""Render the agent's JSON result as the pull request comment.

Runs in the unprivileged CI job; the privileged job only posts the text.
Report text comes from the model, which read the PR's code, so it is
untrusted: mentions and HTML are neutralised before it reaches GitHub.
"""

import argparse
import json
import re
from pathlib import Path

from .errors import ExitCode

MARKER = "<!-- taskly-test-agent -->"

_STATUS = {
    ExitCode.OK: "✅ Tests written and passing",
    ExitCode.CONFIG: "⚠️ Configuration error",
    ExitCode.PROVIDER_TRANSIENT: "⚠️ Model provider unavailable (retries exhausted)",
    ExitCode.PROVIDER_FATAL: "❌ Model provider error",
    ExitCode.AGENT_FAILED: "❌ Agent failed",
    ExitCode.TESTS_FAILED: "❌ Generated tests fail or were not run; not committed",
}


def _safe(text: str) -> str:
    text = re.sub(r"[<>]", "", text)  # no raw HTML, no fake MARKER comments
    text = text.replace("@", "@\u200b")  # no mentions of people or teams
    return text.replace("|", "\\|").replace("\n", " ")


def render(result: dict | None, exit_code: int, usage: str, run_url: str) -> str:
    status = _STATUS.get(exit_code, f"❌ Agent crashed (exit code {exit_code})")
    lines = [MARKER, "## 🧪 Test agent", "", f"**{status}** · [run log]({run_url})", ""]
    if result is None:
        lines.append("The agent produced no result; see the run log.")
        return "\n".join(lines) + "\n"

    plan = result.get("plan")
    if not result.get("agent_ran"):
        lines.append("No changed source file needs unit tests; the model was not called.")
    if plan and plan["skipped"]:
        lines += ["<details><summary>Skipped files</summary>", ""]
        lines += [f"- `{s['path']}`: {s['reason']}" for s in plan["skipped"]]
        lines += ["", "</details>", ""]
    if error := result.get("error"):
        lines += [f"**Error** `{error['kind']}`: {_safe(error['message'])}", ""]

    if report := result.get("report"):
        lines += [f"> {_safe(report['summary'])}", ""]
        if report["decisions"]:
            lines += ["| Source | Action | Reason |", "|---|---|---|"]
            lines += [
                f"| `{_safe(d['path'])}` | {d['action']} | {_safe(d['reason'])} |"
                for d in report["decisions"]
            ]
            lines.append("")
        if report["skills_used"]:
            skills = ", ".join(f"`{_safe(s)}`" for s in report["skills_used"])
            lines += [f"Skills used: {skills}", ""]

    # Recorded by the tools, not claimed by the model.
    if runs := result.get("test_runs"):
        lines += ["| Test run | Files | Result |", "|---|---|---|"]
        for run in runs:
            files = "<br>".join(f"`{p}`" for p in run["paths"])
            verdict = "✅ passed" if run["passed"] else f"❌ exit {run['exit_code']}"
            lines.append(f"| {run['target']} | {files} | {verdict} |")
        lines.append("")
    if unverified := result.get("unverified_tests"):
        lines += ["Failing or never run:", *[f"- `{p}`" for p in unverified], ""]
    if written := result.get("files_written"):
        where = "committed to this branch" if exit_code == ExitCode.OK else "attached as a patch in the run artifacts"
        lines += [f"Files written ({where}):", *[f"- `{p}`" for p in written], ""]

    if usage.strip():
        lines += ["<details><summary>Usage</summary>", "", "```", usage.strip(), "```", "", "</details>"]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskly-pr-comment")
    parser.add_argument("--result", type=Path, required=True, help="agent stdout (JSON)")
    parser.add_argument("--stderr", type=Path, required=True, help="agent stderr")
    parser.add_argument("--exit-code", type=int, required=True)
    parser.add_argument("--run-url", required=True)
    args = parser.parse_args()

    try:
        result = json.loads(args.result.read_text())
    except (OSError, ValueError):
        result = None
    stderr = args.stderr.read_text() if args.stderr.exists() else ""
    usage = stderr[stderr.find("── usage:"):] if "── usage:" in stderr else ""
    print(render(result, args.exit_code, usage, args.run_url), end="")
