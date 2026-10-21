import argparse
import json
import os
import sys
from dataclasses import asdict
from pathlib import Path

from pydantic_ai import RunUsage
from pydantic_ai.usage import UsageLimits

from .agent import Deps, agent
from .changes import GitError, Plan, plan_for_diff, plan_for_untested, render_task
from .errors import ExitCode, Failure, classify
from .usage import format_usage
from .verbose import print_tool_events


def _plan_json(plan: Plan | None) -> dict | None:
    return asdict(plan) if plan is not None else None


def main() -> None:
    parser = argparse.ArgumentParser(prog="taskly-test-agent")
    task = parser.add_mutually_exclusive_group(required=True)
    task.add_argument("prompt", nargs="?", help="free-form task for the agent")
    task.add_argument("--diff", metavar="BASE", help="PR mode: test files changed since BASE")
    task.add_argument(
        "--untested", action="store_true", help="backfill mode: test every source file without tests"
    )
    parser.add_argument("--head", default="HEAD", help="head ref for --diff (default: HEAD)")
    parser.add_argument(
        "--plan-only", action="store_true", help="print the change plan and exit without the model"
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--model",
        default=os.environ.get("AGENT_MODEL"),
        help="provider:model, e.g. openai:gpt-5 (default: $AGENT_MODEL)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print each tool call to stderr"
    )
    parser.add_argument(
        "--max-requests", type=int, default=50, help="model request budget for one run (default: 50)"
    )
    parser.add_argument(
        "--debug", action="store_true", help="show full tracebacks instead of one-line errors"
    )
    args = parser.parse_args()
    repo_root = args.repo.resolve()

    plan: Plan | None = None
    if args.diff or args.untested:
        try:
            plan = plan_for_diff(repo_root, args.diff, args.head) if args.diff else plan_for_untested(repo_root)
        except GitError as exc:
            print(f"error [git]: {exc}", file=sys.stderr)
            sys.exit(ExitCode.CONFIG)
        if args.plan_only or plan.is_empty:
            # No model call: nothing to test (or only the plan was asked for) costs no tokens.
            print(json.dumps({"plan": _plan_json(plan), "agent_ran": False}, indent=2))
            sys.exit(ExitCode.OK)
    elif args.plan_only:
        parser.error("--plan-only needs --diff or --untested")

    if not args.model:
        parser.error("set --model or AGENT_MODEL")

    # Passed in (not read from the result) so tokens are reported even when the run fails.
    usage = RunUsage()
    deps = Deps(repo_root=repo_root)
    try:
        result = agent.run_sync(
            render_task(plan) if plan is not None else args.prompt,
            model=args.model,
            deps=deps,
            usage=usage,
            usage_limits=UsageLimits(request_limit=args.max_requests),
            event_stream_handler=print_tool_events if args.verbose else None,
        )
    except Exception as exc:
        failure = classify(exc)
        # Files may already be written: report them so CI knows what changed.
        print(json.dumps(_run_json(plan, deps, report=None, error=failure), indent=2))
        if failure is None or args.debug:
            raise
        print(failure, file=sys.stderr)
        sys.exit(failure.code)
    finally:
        print(format_usage(usage, args.model), file=sys.stderr)
    unverified = _unverified_tests(deps)
    output = _run_json(plan, deps, report=result.output.model_dump(), error=None)
    output["unverified_tests"] = unverified
    print(json.dumps(output, indent=2))
    if unverified:
        print(f"error [tests_failed]: {', '.join(unverified)}", file=sys.stderr)
        sys.exit(ExitCode.TESTS_FAILED)
    sys.exit(ExitCode.OK)


def _run_json(plan: Plan | None, deps: Deps, report: dict | None, error: Failure | None) -> dict:
    return {
        "plan": _plan_json(plan),
        "agent_ran": True,
        "report": report,
        "error": {"kind": error.kind, "message": error.message} if error is not None else None,
        # Facts recorded by the tools, independent of what the model reports.
        "files_written": deps.written,
        "test_runs": [
            {"target": r.target, "paths": list(r.paths), "exit_code": r.exit_code, "passed": r.passed}
            for r in deps.test_runs
        ],
    }


def _unverified_tests(deps: Deps) -> list[str]:
    """Written test files whose last run failed, or that were never run."""
    last_passed: dict[str, bool] = {}
    for run in deps.test_runs:
        for path in run.paths:
            last_passed[path] = run.passed
    return [
        path
        for path in deps.written
        if Path(path).name != "__init__.py" and not last_passed.get(path, False)
    ]
