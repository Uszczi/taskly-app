import argparse
import os
from pathlib import Path

from . import commands


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskly-claude-ci")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--out",
        type=Path,
        required=True,
        help="directory for plan, result, patch and logs",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    prompt = subcommands.add_parser("prompt", help="write the plan and Claude's prompt")
    prompt.add_argument(
        "--base", required=True, help="PR base SHA; the diff starts at the merge base"
    )
    prompt.add_argument(
        "--schema", type=Path, required=True, help="the report's JSON schema"
    )

    coverage = subcommands.add_parser(
        "coverage", help="measure the coverage of the changed areas"
    )
    coverage.add_argument("name", choices=["before", "after"])
    coverage.add_argument(
        "--base", required=True, help="PR base SHA; the diff starts at the merge base"
    )

    verify_cmd = subcommands.add_parser(
        "verify", help="check Claude's changes and rerun its tests"
    )
    verify_cmd.add_argument(
        "--conclusion", default="", help="claude-code-action's conclusion output"
    )

    comment = subcommands.add_parser("comment", help="print the PR comment")
    comment.add_argument("--run-url", required=True)
    comment.add_argument("--model", required=True)
    comment.add_argument(
        "--execution-file",
        type=lambda value: Path(value) if value else None,
        default="",
        help="claude-code-action's execution file; empty when Claude did not run",
    )

    args = parser.parse_args()
    repo = args.repo.resolve()
    out = args.out
    out.mkdir(parents=True, exist_ok=True)

    if args.command == "prompt":
        print(commands.prompt(repo, args.base, args.schema, out))
    elif args.command == "coverage":
        print(commands.coverage(repo, args.base, out, args.name))
    elif args.command == "verify":
        print(commands.verify(repo, out, os.getenv("REPORT"), args.conclusion))
    elif args.command == "comment":
        print(commands.comment(out, args.run_url, args.execution_file, args.model))
