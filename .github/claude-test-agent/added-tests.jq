# Names of the tests a patch adds, from `jq -Rn -f added-tests.jq < tests.patch`:
# [{path, name}] in patch order. Same rules as added_tests in
# test-agent/src/taskly_test_agent/pr_comment.py.
reduce inputs as $line ({path: null, tests: []};
  if ($line | test("^diff --git ")) then
    .path = ($line | capture("^diff --git a/.+ b/(?<p>.+)$").p)
  elif .path == null then .
  elif ($line | test("^\\+\\s*(it|test)(\\.\\w+)?\\(\\s*['\"`]")) then
    .tests += [{path, name: ($line | capture("^\\+\\s*(?:it|test)(?:\\.\\w+)?\\(\\s*(?<q>['\"`])(?<n>.+?)\\k<q>").n)}]
  elif ($line | test("^\\+\\s*(async\\s+)?def\\s+test_\\w+\\s*\\(")) then
    .tests += [{path, name: ($line | capture("def\\s+test_(?<n>\\w+)").n | gsub("_"; " "))}]
  else . end)
| .tests
