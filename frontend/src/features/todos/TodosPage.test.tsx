import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { useNotice } from '../../hooks/useNotice'
import { useClearCompletedMutation } from './hooks/useClearCompletedMutation'
import { useTodoFilters } from './hooks/useTodoFilters'
import { useTodoStatsQuery } from './hooks/useTodoStatsQuery'
import { useTodosBusy } from './hooks/useTodosBusy'
import { useTodosQuery } from './hooks/useTodosQuery'
import { useUpdateTodoMutation } from './hooks/useUpdateTodoMutation'
import { TodosPage } from './TodosPage'

vi.mock('../../design-system', () => import('../../design-system/mocks'))
vi.mock('../../hooks/useNotice', () => ({ useNotice: vi.fn() }))
vi.mock('./hooks/useTodoFilters', () => ({ useTodoFilters: vi.fn() }))
vi.mock('./hooks/useTodosBusy', () => ({ useTodosBusy: vi.fn() }))
vi.mock('./hooks/useTodosQuery', () => ({ useTodosQuery: vi.fn() }))
vi.mock('./hooks/useTodoStatsQuery', () => ({ useTodoStatsQuery: vi.fn() }))
vi.mock('./hooks/useClearCompletedMutation', () => ({
  useClearCompletedMutation: vi.fn(),
}))
vi.mock('./hooks/useUpdateTodoMutation', () => ({
  useUpdateTodoMutation: vi.fn(),
}))
vi.mock('./components/TodosHeader', () => ({
  TodosHeader: () => <h1>Tasks</h1>,
}))
// Stand-in that exposes the page's clear handler without its own busy guard,
// so the page-level guard is what gets exercised.
vi.mock('./components/TodoSummary', () => ({
  TodoSummary: ({ onClearCompleted }: { onClearCompleted: () => void }) => (
    <button onClick={onClearCompleted}>Clear completed stub</button>
  ),
}))
vi.mock('./components/TodoFilters', () => ({ TodoFilters: () => null }))
vi.mock('./components/TodoList', () => ({ TodoList: () => <p>Task list</p> }))
vi.mock('./components/TodoEditor', () => ({ TodoEditor: () => null }))
vi.mock('./components/DeleteTodoDialog', () => ({
  DeleteTodoDialog: () => null,
}))
vi.mock('../../components/SuccessNotice', () => ({ SuccessNotice: () => null }))

interface PageOptions {
  queryError?: Error | null
  busy?: boolean
  notify?: ReturnType<typeof vi.fn>
  refetch?: ReturnType<typeof vi.fn>
  toggleReset?: ReturnType<typeof vi.fn>
  clearReset?: ReturnType<typeof vi.fn>
  clearMutateAsync?: ReturnType<typeof vi.fn>
  clearError?: Error | null
}

function renderPage({
  queryError = null,
  busy = false,
  notify = vi.fn(),
  refetch = vi.fn().mockResolvedValue(undefined),
  toggleReset = vi.fn(),
  clearReset = vi.fn(),
  clearMutateAsync = vi.fn().mockResolvedValue({ deleted: 2 }),
  clearError = null,
}: PageOptions = {}) {
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: queryError !== null,
    error: queryError,
    refetch,
  } as unknown as ReturnType<typeof useTodosQuery>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    error: null,
    reset: toggleReset,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  vi.mocked(useTodoStatsQuery).mockReturnValue({
    data: undefined,
  } as unknown as ReturnType<typeof useTodoStatsQuery>)
  vi.mocked(useClearCompletedMutation).mockReturnValue({
    error: clearError,
    reset: clearReset,
    mutateAsync: clearMutateAsync,
  } as unknown as ReturnType<typeof useClearCompletedMutation>)
  vi.mocked(useTodosBusy).mockReturnValue(busy)
  vi.mocked(useNotice).mockReturnValue({ message: '', notify })
  vi.mocked(useTodoFilters).mockReturnValue({
    filter: 'all',
    search: '',
    sort: 'newest',
    visible: [],
    setFilter: vi.fn(),
    setSearch: vi.fn(),
    setSort: vi.fn(),
  })
  render(<TodosPage />)
  return { notify, refetch, toggleReset, clearReset, clearMutateAsync }
}

beforeEach(() => vi.clearAllMocks())

it('displays a query failure and resets mutation errors before retrying', async () => {
  const user = userEvent.setup()
  const { refetch, toggleReset, clearReset } = renderPage({
    queryError: new Error('The server is unavailable.'),
  })
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1))
  expect(toggleReset).toHaveBeenCalledTimes(1)
  expect(clearReset).toHaveBeenCalledTimes(1)
  expect(toggleReset.mock.invocationCallOrder[0]).toBeLessThan(
    refetch.mock.invocationCallOrder[0],
  )
  expect(clearReset.mock.invocationCallOrder[0]).toBeLessThan(
    refetch.mock.invocationCallOrder[0],
  )
})

it('clears completed tasks and reports how many were removed', async () => {
  const user = userEvent.setup()
  const { notify, clearMutateAsync } = renderPage()
  await user.click(screen.getByRole('button', { name: 'Clear completed stub' }))
  await waitFor(() =>
    expect(notify).toHaveBeenCalledWith('Cleared 2 completed tasks.'),
  )
  expect(clearMutateAsync).toHaveBeenCalledTimes(1)
})

it('uses the singular notice when one completed task is cleared', async () => {
  const user = userEvent.setup()
  const { notify } = renderPage({
    clearMutateAsync: vi.fn().mockResolvedValue({ deleted: 1 }),
  })
  await user.click(screen.getByRole('button', { name: 'Clear completed stub' }))
  await waitFor(() =>
    expect(notify).toHaveBeenCalledWith('Cleared 1 completed task.'),
  )
})

it('does not clear completed tasks while another change is in progress', async () => {
  const user = userEvent.setup()
  const { notify, clearMutateAsync } = renderPage({ busy: true })
  await user.click(screen.getByRole('button', { name: 'Clear completed stub' }))
  expect(clearMutateAsync).not.toHaveBeenCalled()
  expect(notify).not.toHaveBeenCalled()
})

it('shows a failed clear in the page alert and announces no success', async () => {
  const user = userEvent.setup()
  const failure = new Error('Could not clear completed tasks.')
  const { notify, clearMutateAsync } = renderPage({
    clearError: failure,
    clearMutateAsync: vi.fn().mockRejectedValue(failure),
  })
  await user.click(screen.getByRole('button', { name: 'Clear completed stub' }))
  await waitFor(() => expect(clearMutateAsync).toHaveBeenCalledTimes(1))
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'Could not clear completed tasks.',
  )
  expect(notify).not.toHaveBeenCalled()
})
