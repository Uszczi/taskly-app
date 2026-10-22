## Running in Claude Code on CI

No one answers questions or approves tool calls.

### Tools

- Explore with Read, Glob and Grep. Write with Edit or Write.
- Bash runs only the test and typecheck commands from the backend and frontend
  skills, typed exactly as there: one command per call, from the repository
  root, with nothing around it (no `cd`, `&&`, pipes or redirects). Every other
  call is refused at once, and a refused call stays refused: change the call
  instead of repeating it.
- Tests run sandboxed: no network, no credentials, read-only outside the
  checkout. Mock what a test would otherwise reach for.

### Steps

Your turns are limited, and the task already holds each file's diff.

1. For each source file, read it and its existing test. Read further only what
   a test needs: fixtures, mocks, the types it builds.
2. Write an area's test files, then run them together in one call (for the
   frontend, follow with the typecheck). Fix and rerun until green.

### What happens after you

Every file you write is final: you cannot delete or rename it. All of them are
rerun together, with the typecheck, and if any fails, none is proposed. So:

- create files only at the test paths the task lists, plus the shared fixtures
  and helpers the skills call for;
- keep a failing test only for a production bug you are sure of, and name the
  bug in `attention`: the PR then shows the failure instead of new tests.

You are done when every source file in the task has a decision in the report,
and each area's last run covers every file you wrote there and is green, or
red only for a bug named in `attention`.
