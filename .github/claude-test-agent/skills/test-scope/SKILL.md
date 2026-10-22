---
name: test-scope
description: Decide which files a Taskly pull request changes deserve unit tests and which to skip. Load this first, before writing any test.
---

# Deciding what to test

You write **unit test files only**; production code, configuration, and
unrelated existing tests stay as they are.

## Scope

Each file in the task comes with its diff, and the scope is the behavior that
diff adds or changes. Tests pin the new behavior where it is observable: a
changed mapping is asserted where a component renders it, not only as a
constant. Untouched code in the same file keeps its current tests.

A change to a skipped file (a design-system component, a type) is tested
through the listed file that uses it.

## Files to skip

The coverage exclusions are the source of truth: `omit` in
`backend/pyproject.toml` and `coverage.exclude` in `frontend/vite.config.ts`.
A task plan already has them filtered out. Also skip changes with no behavior:
pure re-exports, type-only changes, comments, formatting.

## Files worth testing

Anything with behavior: branches, validation, data mapping, error handling,
hooks with side effects, components that react to user input.

## Decision per file

Read the source file and its existing test, then decide one of:

- **add**: no test file exists yet. Backend tests mirror the source path under
  `backend/tests/` with a `test_` prefix; frontend tests sit next to the source
  as `<Name>.test.ts(x)`.
- **update**: a test file exists but does not cover the behavior in scope.
  Extend it, keeping the tests that still pass and still make sense.
- **skip**: the file is excluded or has no testable behavior. Say why.

## Shared setup

When two or more test files need the same setup (a fixture, a wrapped client, a
builder for test data), write it once where they can all use it: a fixture in a
`conftest.py` (backend skill), a helper in `frontend/src/test/` (frontend
skill). Look there first and reuse what exists. A change to shared test code
reruns every test in its area, so keep the existing fixtures and helpers working.

## Behavioral tests

Write a few precise *behavioral* tests rather than many shallow ones:

- Each test asserts observable behavior: return values, rendered output,
  HTTP responses, calls on mocked boundaries.
- Each test has a real assertion that can fail.
- Inputs are controlled: mocked network and database, `tmp_path` for files,
  fixed times.
- A test that fails because the production code is wrong stays as written and
  is reported as a production bug.

## Done

Every file in the plan has exactly one `add`/`update`/`skip` decision in the
report, every behavior in scope has a test that fails without it, and every
test file you wrote ends either *green* (see each area's skill for how to run
it) or reported as a production bug.
