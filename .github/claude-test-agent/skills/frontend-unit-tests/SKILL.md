---
name: frontend-unit-tests
description: Conventions for writing Vitest + React Testing Library unit tests for the Taskly React/TypeScript frontend (frontend/src). Load before writing or updating any frontend test.
---

# Frontend unit tests (Vitest + React Testing Library)

## Layout

- Tests sit next to the source: `src/hooks/useNotice.ts` → `src/hooks/useNotice.test.ts`,
  components use `.test.tsx`.
- Environment is jsdom; `src/test/setup.ts` already loads `@testing-library/jest-dom`
  matchers and runs `cleanup` after each test.
- Import test APIs explicitly: `import { expect, it, vi } from 'vitest'`.

## Shared helpers

- `src/test/` holds what several test files share. Add a helper or fixture
  there instead of repeating it, and reuse what is already there.
- `src/test/todoFixture.ts` exports `todoFixture: Todo`. Spread and override it
  (`{ ...todoFixture, completed: true }`) instead of building todos by hand.
- Any other object several tests build (e.g. a `TodoStats`) gets the same
  treatment: one fixture in `src/test/<name>Fixture.ts`, spread and overridden
  in every test that needs it, never rebuilt inline.
- Design-system components are mocked with their own module. Every component
  test that renders design-system UI starts with (path relative to the test):
  `vi.mock('../../../design-system', () => import('../../../design-system/mocks'))`

## Style

- Top-level `it('does something observable', ...)` blocks.
- Query by role and accessible name: `screen.getByRole('button', { name: 'Edit: …' })`.
- Interact with `const user = userEvent.setup()` and `await user.click(...)`.
- Callbacks are `vi.fn()`; assert both what was called and what was not.
- Mock modules at their import path with `vi.mock(...)` and type them with
  `vi.mocked(fn)`. Reset with `beforeEach(() => vi.clearAllMocks())`.
- When mocking a hook's return value, cast partial objects:
  `as unknown as ReturnType<typeof useTodosQuery>`.

## Hooks

- Plain hooks: `renderHook(() => useThing())` and `act(...)` for updates.
- TanStack Query hooks (`useTodosQuery`, `use*Mutation`) need a provider with a
  fresh client per test, retries off. Use `createQueryWrapper` from
  `src/test/queryClient.tsx`; if that file does not exist yet, create it:

```tsx
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import type { ReactNode } from 'react'

export function createQueryWrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
  return { client, wrapper }
}
```

  `const { client, wrapper } = createQueryWrapper()`, then
  `renderHook(() => useThing(), { wrapper })`. Mock the API layer
  (`vi.mock('../api/todos', ...)`). To assert cache updates, read
  `client.getQueryData(todoKeys.list)`.

## Example

```tsx
it('forwards edit requests', async () => {
  const user = userEvent.setup()
  const onEdit = vi.fn()
  render(<TodoItem todo={todoFixture} busy={false} onEdit={onEdit} onToggle={vi.fn()} onDelete={vi.fn()} />)
  await user.click(screen.getByRole('button', { name: `Edit: ${todoFixture.title}` }))
  expect(onEdit).toHaveBeenCalledTimes(1)
})
```

## Running

From the repository root, with test paths relative to `frontend/` (the whole
suite is `src`), then the typecheck (vitest does not check types; a run passes
only when both pass):

```bash
frontend/node_modules/.bin/vitest run --root frontend src/hooks/useNotice.test.ts
frontend/node_modules/.bin/vitest run --root frontend src
frontend/node_modules/.bin/tsc --noEmit -p frontend
```
