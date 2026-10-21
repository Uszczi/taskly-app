# Names of the tests a patch adds, from `jq -Rn -f added-tests.jq < tests.patch`:
# [{path, name}] in patch order. Same rules as added_tests in
# test-agent/src/taskly_test_agent/pr_comment.py: a name the patch also removes
# from the same file is an existing test that was moved or rewritten.
def js_test: "^(?<sign>[+-])\\s*(?:it|test)(?:\\.\\w+)?\\(\\s*(?<q>['\"`])(?<name>.+?)\\k<q>";
def py_test: "^(?<sign>[+-])\\s*(?:async\\s+)?def\\s+test_(?<name>\\w+)\\s*\\(";

reduce inputs as $line ({path: null, added: [], removed: []};
  if ($line | test("^diff --git ")) then
    .path = ($line | capture("^diff --git a/.+ b/(?<p>.+)$").p)
  elif .path == null then .
  else
    (if ($line | test(js_test)) then ($line | capture(js_test))
     elif ($line | test(py_test)) then ($line | capture(py_test) | .name |= gsub("_"; " "))
     else null end) as $match
    | if $match == null then .
      elif $match.sign == "+" then .added += [{path, name: $match.name}]
      else .removed += [{path, name: $match.name}] end
  end)
| .removed as $removed
| [.added[] | select(. as $t | $removed | index([$t]) | not)]
