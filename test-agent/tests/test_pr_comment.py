from taskly_test_agent.errors import ExitCode
from taskly_test_agent.pr_comment import COMMIT_SLOT, MARKER, added_tests, render

RESULT = {
    "plan": {"targets": [], "skipped": [{"path": "README.md", "reason": "not backend or frontend source"}], "changed_tests": []},
    "agent_ran": True,
    "report": {
        "summary": "Added tests.",
        "decisions": [{"path": "backend/app/x.py", "action": "add", "reason": "new module"}],
        "attention": ["x.py drops <b>empty</b> titles silently <!-- commit --> cc @org/team"],
        "skills_used": ["backend-unit-tests"],
    },
    "error": None,
    "files_written": ["backend/tests/test_x.py"],
    "test_runs": [{"target": "backend", "paths": ["backend/tests/test_x.py"], "exit_code": 0, "passed": True}],
    "unverified_tests": [],
}

PATCH = """\
diff --git a/frontend/src/a/Item.test.tsx b/frontend/src/a/Item.test.tsx
--- a/frontend/src/a/Item.test.tsx
+++ b/frontend/src/a/Item.test.tsx
 it('already existed', () => {})
+it('tints the card by priority', () => {
+describe('group', () => {
+  it.skip("skipped one", () => {})
diff --git a/backend/tests/test_x.py b/backend/tests/test_x.py
+def test_rejects_empty_title(client):
+    async def test_lists_todos():
+def helper():
"""

USAGE = "── usage: anthropic:claude-haiku-5-5 ──\nrequests:        7\ncost:            $0.007696\n"


def test_moved_or_rewritten_tests_are_not_counted_as_added() -> None:
    patch = """\
diff --git a/frontend/src/a/Item.test.tsx b/frontend/src/a/Item.test.tsx
-it('shows an active task', async () => {
+describe('Item', () => {
+  it('shows an active task', async () => {
+  it('tints the card', () => {
diff --git a/backend/tests/test_x.py b/backend/tests/test_x.py
-def test_lists_todos(client):
+def test_lists_todos(client, todo):
"""

    assert added_tests(patch) == {"frontend/src/a/Item.test.tsx": ["tints the card"]}


def test_added_tests_reads_new_test_names_per_file() -> None:
    assert added_tests(PATCH) == {
        "frontend/src/a/Item.test.tsx": ["tints the card by priority", "skipped one"],
        "backend/tests/test_x.py": ["rejects empty title", "lists todos"],
    }


def test_success_lists_covered_behaviors_and_leaves_a_commit_slot() -> None:
    body = render(RESULT, ExitCode.OK, USAGE, "https://run", PATCH)

    assert body.startswith(MARKER)
    assert "## 🧪 Test agent: ✅ 4 tests added, passing" in body
    assert f"[run log](https://run){COMMIT_SLOT}" in body
    assert "**Now covered**" in body
    assert "- `Item.test.tsx`\n  - tints the card by priority" in body
    assert "  - rejects empty title" in body
    assert "<sub>anthropic:claude-haiku-5-5 · $0.007696 · 7 requests</sub>" in body


def test_only_reviewer_facing_text_is_shown() -> None:
    body = render(RESULT, ExitCode.OK, USAGE, "https://run", PATCH)

    for internal in ("README.md", "Added tests.", "new module", "backend-unit-tests"):
        assert internal not in body


def test_model_text_cannot_mention_people_forge_markers_or_inject_html() -> None:
    body = render(RESULT, ExitCode.OK, "", "https://run", PATCH)

    assert body.count(MARKER) == 1 and body.count(COMMIT_SLOT) == 1
    assert "<b>" not in body
    assert "@org" not in body and "@​org" in body


def test_attention_is_hidden_when_there_is_nothing_to_flag() -> None:
    result = {**RESULT, "report": {**RESULT["report"], "attention": []}}

    assert "Needs your attention" not in render(result, ExitCode.OK, "", "https://run", PATCH)


def test_failed_tests_are_flagged_and_not_reported_as_covered() -> None:
    result = {**RESULT, "unverified_tests": ["backend/tests/test_x.py"]}

    body = render(result, ExitCode.TESTS_FAILED, "", "https://run", PATCH)

    assert "not committed" in body
    assert "**Written, not committed**" in body and "Now covered" not in body
    assert "- `backend/tests/test_x.py` fails or was never run." in body


def test_success_without_new_tests_says_none_were_needed() -> None:
    assert "✅ No new tests needed" in render(RESULT, ExitCode.OK, "", "https://run")


def test_missing_result_points_to_the_log() -> None:
    body = render(None, 1, "", "https://run")

    assert "exit code 1" in body and "see the run log" in body


def test_skipped_run_says_nothing_needs_tests() -> None:
    body = render({"plan": RESULT["plan"], "agent_ran": False}, ExitCode.OK, "", "https://run")

    assert "No changed source file needs unit tests" in body



def test_changed_files_excluded_from_coverage_get_a_table() -> None:
    plan = {"targets": [], "changed_tests": [], "skipped": [
        {"path": "frontend/src/design-system/Tag.tsx", "reason": "excluded from frontend coverage", "excluded": True},
        {"path": "docs/new.md", "reason": "not backend or frontend source", "excluded": False},
    ]}

    body = render({**RESULT, "plan": plan}, ExitCode.OK, "", "https://run", PATCH)

    assert "**Changed files without tests**" in body
    assert "| `frontend/src/design-system/Tag.tsx` | excluded from frontend coverage |" in body
    assert "docs/new.md" not in body


def test_no_table_when_only_non_source_files_are_skipped() -> None:
    assert "Changed files without tests" not in render(RESULT, ExitCode.OK, "", "https://run", PATCH)


def test_model_skips_join_the_table_but_other_decisions_stay_out() -> None:
    plan = {"targets": [], "changed_tests": [], "skipped": [
        {"path": "frontend/src/design-system/Tag.tsx", "reason": "excluded from frontend coverage", "excluded": True},
    ]}
    decisions = [
        {"path": "frontend/src/a/todos.ts", "action": "skip", "reason": "only a constant | tested via Item"},
        {"path": "backend/app/x.py", "action": "add", "reason": "new module"},
    ]
    result = {**RESULT, "plan": plan, "report": {**RESULT["report"], "decisions": decisions}}

    body = render(result, ExitCode.OK, "", "https://run", PATCH)

    assert "| `frontend/src/design-system/Tag.tsx` | excluded from frontend coverage |" in body
    assert "| `frontend/src/a/todos.ts` | only a constant \\| tested via Item |" in body
    assert "backend/app/x.py" not in body and "new module" not in body
