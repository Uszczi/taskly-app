import json
from pathlib import Path

from . import verify as verification
from .comment import denied_calls, render, usage_footer
from .coverage import measure
from .github import multiline_output, output
from .json import read_json, write_json
from .models import Coverage, Execution, Plan, Result, SkipRules
from .plan import SKIP_RULES, build_plan, render_task


def prompt(repo: Path, base: str, schema: Path, out: Path) -> str:
    rules = SkipRules.model_validate_json((repo / SKIP_RULES).read_text())
    plan = build_plan(repo, base, rules)
    write_json(out / "plan.json", plan)
    if not plan.targets:
        write_json(out / "result.json", Result(status="nothing_to_test"))
        return output("has_targets", "false")
    text = f"{render_task(plan)}\n"
    (out / "prompt.md").write_text(text)
    compact_schema = json.dumps(json.loads(schema.read_text()), separators=(",", ":"))
    return "\n".join(
        [
            output("has_targets", "true"),
            multiline_output("prompt", text),
            output("schema", compact_schema),
        ]
    )


def coverage(repo: Path, base: str, out: Path, name: str) -> str:
    logs = out / f"coverage-{name}"
    logs.mkdir(exist_ok=True)
    return write_json(out / f"coverage-{name}.json", measure(repo, base, logs))


def verify(repo: Path, out: Path, report: str | None, conclusion: str) -> str:
    result = verification.verify(repo, out, report, conclusion)
    write_json(out / "result.json", result)
    return output("status", result.status)


def comment(out: Path, run_url: str, execution_file: Path | None, model: str) -> str:
    patch = out / "tests.patch"
    execution = (read_json(execution_file, Execution) or Execution([])).root
    text = render(
        result=read_json(out / "result.json", Result),
        plan=read_json(out / "plan.json", Plan) or Plan(),
        patch=patch.read_text() if patch.exists() else "",
        before=read_json(out / "coverage-before.json", Coverage) or Coverage(),
        after=read_json(out / "coverage-after.json", Coverage) or Coverage(),
        run_url=run_url,
        footer=usage_footer(execution, model),
        denied=denied_calls(execution),
    )
    (out / "comment.md").write_text(text)
    return text
