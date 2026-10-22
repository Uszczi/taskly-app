from typing import Literal

from pydantic import BaseModel, RootModel

Area = Literal["backend", "frontend"]
Status = Literal["ok", "tests_failed", "violation", "agent_failed", "nothing_to_test"]


class BackendRules(BaseModel):
    root: str
    suffixes: list[str]
    skip_names: list[str]
    skip_paths: list[str]


class FrontendRules(BaseModel):
    root: str
    suffixes: list[str]
    skip_globs: list[str]


class SkipRules(BaseModel):
    backend: BackendRules
    frontend: FrontendRules


class Target(BaseModel):
    source: str
    area: Area
    test: str
    test_exists: bool
    diff: str


class Skipped(BaseModel):
    path: str
    reason: str
    excluded: bool


class Plan(BaseModel):
    targets: list[Target] = []
    skipped: list[Skipped] = []
    changed_tests: list[str] = []


class Decision(BaseModel):
    path: str
    action: Literal["add", "update", "skip"]
    reason: str


class Report(BaseModel):
    summary: str
    decisions: list[Decision]
    attention: list[str]
    skills_used: list[str]


class Run(BaseModel):
    target: Literal["backend", "frontend", "typecheck"]
    exit_code: int


class AreaCoverage(BaseModel):
    total: float
    files: dict[str, float]


class Coverage(BaseModel):
    backend: AreaCoverage | None = None
    frontend: AreaCoverage | None = None


class Result(BaseModel):
    status: Status
    written: list[str] = []
    violations: list[str] = []
    runs: list[Run] = []
    report: Report | None = None


class ExecutionEntry(BaseModel):
    type: str = ""
    total_cost_usd: float | None = None
    num_turns: int | None = None
    permission_denials: list[object] = []


Execution = RootModel[list[ExecutionEntry]]
