"""Shapes of the JSON files the commands pass to each other through the out directory.

`prompt` writes plan.json (and, with nothing to test, result.json); `verify`
writes result.json; `comment` reads both.
"""

from typing import Literal, NotRequired, TypedDict

Area = Literal["backend", "frontend"]
Status = Literal["ok", "tests_failed", "violation", "agent_failed", "nothing_to_test"]


class BackendRules(TypedDict):
    root: str
    suffixes: list[str]
    skip_names: list[str]
    skip_paths: list[str]


class FrontendRules(TypedDict):
    root: str
    suffixes: list[str]
    skip_globs: list[str]  # fnmatch globs: `*` also matches `/`


class SkipRules(TypedDict):
    """agent-shared/skip-rules.json (its `$comment` keys are not read)."""

    backend: BackendRules
    frontend: FrontendRules


class Target(TypedDict):
    """A changed source file that needs tests."""

    source: str
    area: Area
    test: str  # conventional test path, existing or to be created
    test_exists: bool
    diff: str


class Skipped(TypedDict):
    """A changed file that needs no tests."""

    path: str
    reason: str
    excluded: bool  # source code excluded from coverage, not just a non-source file


class Plan(TypedDict):
    targets: list[Target]
    skipped: list[Skipped]
    changed_tests: list[str]


class Decision(TypedDict):
    path: str
    action: Literal["add", "update", "skip"]
    reason: str


class Report(TypedDict, total=False):
    """Claude's structured output (agent-shared/report.schema.json). Model text: untrusted."""

    summary: str
    decisions: list[Decision]
    attention: list[str]
    skills_used: list[str]


class Run(TypedDict):
    target: Literal["backend", "frontend", "typecheck"]
    exit_code: int


class Result(TypedDict):
    status: Status
    # Absent when `prompt` found nothing to test and Claude never ran.
    written: NotRequired[list[str]]
    violations: NotRequired[list[str]]
    runs: NotRequired[list[Run]]
    report: NotRequired[Report | None]
