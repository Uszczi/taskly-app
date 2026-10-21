from taskly_test_agent.errors import ExitCode
from taskly_test_agent.pr_comment import MARKER, render

RESULT = {
    "plan": {"targets": [], "skipped": [{"path": "README.md", "reason": "not backend or frontend source"}], "changed_tests": []},
    "agent_ran": True,
    "report": {
        "summary": "Added tests. <!-- taskly-test-agent --> cc @org/team",
        "decisions": [{"path": "backend/app/x.py", "action": "add", "reason": "new | module"}],
        "skills_used": ["backend-unit-tests"],
    },
    "error": None,
    "files_written": ["backend/tests/test_x.py"],
    "test_runs": [{"target": "backend", "paths": ["backend/tests/test_x.py"], "exit_code": 0, "passed": True}],
    "unverified_tests": [],
}


def test_renders_decisions_runs_and_files() -> None:
    body = render(RESULT, ExitCode.OK, "── usage: m ──\ncost: $0.01", "https://run")

    assert body.startswith(MARKER)
    assert "✅ Tests written and passing" in body
    assert "| `backend/app/x.py` | add | new \\| module |" in body
    assert "| backend | `backend/tests/test_x.py` | ✅ passed |" in body
    assert "committed to this branch" in body
    assert "cost: $0.01" in body


def test_model_text_cannot_mention_people_or_forge_the_marker() -> None:
    body = render(RESULT, ExitCode.OK, "", "https://run")

    assert body.count(MARKER) == 1
    assert "@org" not in body and "@​org" in body


def test_failed_tests_are_not_reported_as_committed() -> None:
    result = {**RESULT, "unverified_tests": ["backend/tests/test_x.py"]}

    body = render(result, ExitCode.TESTS_FAILED, "", "https://run")

    assert "not committed" in body and "attached as a patch" in body
    assert "- `backend/tests/test_x.py`" in body


def test_missing_result_points_to_the_log() -> None:
    body = render(None, 1, "", "https://run")

    assert "exit code 1" in body and "see the run log" in body


def test_skipped_run_says_the_model_was_not_called() -> None:
    body = render({"plan": RESULT["plan"], "agent_ran": False}, ExitCode.OK, "", "https://run")

    assert "model was not called" in body and "`README.md`" in body
