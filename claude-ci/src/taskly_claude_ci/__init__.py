"""CLI for the deterministic steps around Claude Code in pr-test-claude.yml.

Independent of the PydanticAI agent: it shares only the data in agent-shared/
(skills, instructions, report schema, skip rules), never code.

- `prompt`: plan.json, and prompt.md (instructions plus the task) when there is
  something to test;
- `verify`: what Claude changed on disk and a sandboxed rerun of its tests;
- `comment`: the PR comment.
"""

import argparse
import os
import sys
from pathlib import Path

from .comment import render, usage_footer
from .plan import write_prompt
from .verify import verify


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskly-claude-ci")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--out", type=Path, required=True, help="directory for plan, result, patch and logs")
    commands = parser.add_subparsers(dest="command", required=True)

    prompt = commands.add_parser("prompt", help="write the plan and Claude's prompt")
    prompt.add_argument("--base", required=True, help="PR base SHA; the diff starts at the merge base")
    prompt.add_argument(
        "--instructions", type=Path, action="append", required=True,
        help="instruction files, in order, before the task (repeatable)",
    )

    verify_cmd = commands.add_parser("verify", help="check Claude's changes and rerun its tests")
    verify_cmd.add_argument("--conclusion", default="", help="claude-code-action's conclusion output")

    comment = commands.add_parser("comment", help="print the PR comment")
    comment.add_argument("--run-url", required=True)
    comment.add_argument("--model", required=True)
    comment.add_argument("--execution-file", type=Path)

    args = parser.parse_args()
    repo = args.repo.resolve()
    args.out.mkdir(parents=True, exist_ok=True)

    # Each command prints `key=value` lines for $GITHUB_OUTPUT, or the comment.
    if args.command == "prompt":
        try:
            has_targets = write_prompt(repo, args.base, args.instructions, args.out)
        except ValueError as exc:
            print(f"error: {exc}", file=sys.stderr)
            sys.exit(2)
        print(f"has_targets={'true' if has_targets else 'false'}")
    elif args.command == "verify":
        # The report is model output: read from the environment, never from a command line.
        print(f"status={verify(repo, args.out, os.environ.get('REPORT'), args.conclusion)}")
    else:
        print(render(args.out, args.run_url, usage_footer(args.execution_file, args.model)), end="")
