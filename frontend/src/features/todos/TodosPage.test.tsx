import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { useNotice } from '../../hooks/useNotice'
import { todoStatsFixture } from '../../test/todoStatsFixture'
import { useClearCompletedMutation } from './hooks/useClearCompletedMutation'
import { useTodoFilters } from './hooks/useTodoFilters'
import { useTodoStatsQuery } from './hooks/useTodoStatsQuery'
import { useTodosBusy } from './hooks/useTodosBusy'
import { useTodosQuery } from './hooks/useTodosQuery'
import { useUpdateTodoMutation } from './hooks/useUpdateTodoMutation'
import { TodosPage } from './TodosPage'

vi.mock('../../design-system', () => import('../../design-system/mocks'))
vi.mock('../../hooks/useNotice', () => ({ useNotice: vi.fn() }))
vi.mock('./hooks/useClearCompletedMutation', () => ({
  useClearCompletedMutation: vi.fn(),
}))
vi.mock('./hooks/useTodoFilters', () => ({ useTodoFilters: vi.fn() }))
vi.mock('./hooks/useTodoStatsQuery', () => ({ useTodoStatsQuery: vi.fn() }))
vi.mock('./hooks/useTodosBusy', () => ({ useTodosBusy: vi.fn() }))
vi.mock('./hooks/useTodosQuery', () => ({ useTodosQuery: vi.fn() }))
vi.mock('./hooks/useUpdateTodoMutation', () => ({
  useUpdateTodoMutation: vi.fn(),
}))
vi.mock('./components/TodosHeader', () => ({
  TodosHeader: () => <h1>Tasks</h1>,
}))
vi.mock('./components/TodoFilters', () => ({ TodoFilters: () => null }))
vi.mock('./components/TodoList', () => ({ TodoList: () => <p>Task list</p> }))
vi.mock('./components/TodoEditor', () => ({ TodoEditor: () => null }))
vi.mock('./components/DeleteTodoDialog', () => ({
  DeleteTodoDialog: () => null,
}))
vi.mock('../../components/SuccessNotice', () => ({ SuccessNotice: () => null }))

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useTodosQuery>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    error: null,
    reset: vi.fn(),
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  vi.mocked(useTodoStatsQuery).mockReturnValue({
    data: todoStatsFixture,
  } as unknown as ReturnType<typeof useTodoStatsQuery>)
  vi.mocked(useTodosBusy).mockReturnValue(false)
  vi.mocked(useTodoFilters).mockReturnValue({
    filter: 'all',
    search: '',
    sort: 'newest',
    visible: [],
    setFilter: vi.fn(),
    setSearch: vi.fn(),
    setSort: vi.fn(),
  })
})

function mockClearCompleted(overrides: {
  mutateAsync?: ReturnType<typeof vi.fn>
  error?: Error | null
  reset?: ReturnType<typeof vi.fn>
}) {
  vi.mocked(useClearCompletedMutation).mockReturnValue({
    error: null,
    reset: vi.fn(),
    mutateAsync: vi.fn(),
    ...overrides,
  } as unknown as ReturnType<typeof useClearCompletedMutation>)
}

it('displays a query failure and resets mutation errors before retrying', async () => {
  const user = userEvent.setup()
  const refetch = vi.fn().mockResolvedValue(undefined)
  const reset = vi.fn()
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: true,
    error: new Error('The server is unavailable.'),
    refetch,
  } as unknown as ReturnType<typeof useTodosQuery>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    error: null,
    reset,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  vi.mocked(useNotice).mockReturnValue({ message: '', notify: vi.fn() })
  mockClearCompleted({})
  render(<TodosPage />)
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1))
  expect(reset).toHaveBeenCalledTimes(1)
  expect(reset.mock.invocationCallOrder[0]).toBeLessThan(
    refetch.mock.invocationCallOrder[0],
  )
})

it('clears completed tasks and announces how many were deleted', async () => {
  const user = userEvent.setup()
  const notify = vi.fn()
  const mutateAsync = vi.fn().mockResolvedValue({ deleted: 2 })
  vi.mocked(useNotice).mockReturnValue({ message: '', notify })
  mockClearCompleted({ mutateAsync })
  render(<TodosPage />)
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  await waitFor(() =>
    expect(notify).toHaveBeenCalledWith('Cleared 2 completed tasks.'),
  )
  expect(mutateAsync).toHaveBeenCalledTimes(1)
})

it('uses the singular notice when exactly one completed task is cleared', async () => {
  const user = userEvent.setup()
  const notify = vi.fn()
  vi.mocked(useNotice).mockReturnValue({ message: '', notify })
  mockClearCompleted({ mutateAsync: vi.fn().mockResolvedValue({ deleted: 1 }) })
  render(<TodosPage />)
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  await waitFor(() =>
    expect(notify).toHaveBeenCalledWith('Cleared 1 completed task.'),
  )
})

it('does not announce a clear that failed', async () => {
  const user = userEvent.setup()
  const notify = vi.fn()
  vi.mocked(useNotice).mockReturnValue({ message: '', notify })
  const mutateAsync = vi
    .fn()
    .mockRejectedValue(new Error('The server is unavailable.'))
  mockClearCompleted({ mutateAsync })
  render(<TodosPage />)
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  await waitFor(() => expect(mutateAsync).toHaveBeenCalledTimes(1))
  expect(notify).not.toHaveBeenCalled()
})

it('shows a failed clear in the page alert', () => {
  vi.mocked(useNotice).mockReturnValue({ message: '', notify: vi.fn() })
  mockClearCompleted({ error: new Error('Clearing failed on the server.') })
  render(<TodosPage />)
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'Clearing failed on the server.',
  )
})

it('resets a failed clear before retrying the list', async () => {
  const user = userEvent.setup()
  const reset = vi.fn()
  const refetch = vi.fn().mockResolvedValue(undefined)
  vi.mocked(useNotice).mockReturnValue({ message: '', notify: vi.fn() })
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: true,
    error: new Error('The server is unavailable.'),
    refetch,
  } as unknown as ReturnType<typeof useTodosQuery>)
  mockClearCompleted({ error: new Error('Clearing failed on the server.'), reset })
  render(<TodosPage />)
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1))
  expect(reset).toHaveBeenCalledTimes(1)
})
