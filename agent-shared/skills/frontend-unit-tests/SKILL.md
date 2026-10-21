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

- `src/test/todoFixture.ts` exports `todoFixture: Todo`. Spread and override it
  (`{ ...todoFixture, completed: true }`) instead of building todos by hand.
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
- TanStack Query hooks (`useTodosQuery`, `use*Mutation`) need a provider. Create
  a fresh client per test with retries off and pass a wrapper:

```tsx
function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
```

  Mock the API layer (`vi.mock('../api/todos', ...)`).
  To assert cache updates, keep a reference to the client and read
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

Call `run_tests` with target `frontend` and paths from the repository root,
e.g. `frontend/src/hooks/useNotice.test.ts`.
