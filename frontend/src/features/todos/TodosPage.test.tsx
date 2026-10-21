import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { useNotice } from '../../hooks/useNotice'
import { todoStatsFixture } from '../../test/todoStatsFixture'
import { TodoSummary } from './components/TodoSummary'
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
vi.mock('./hooks/useUpdateTodoMutation', () => ({
  useUpdateTodoMutation: vi.fn(),
}))
vi.mock('./hooks/useTodoStatsQuery', () => ({ useTodoStatsQuery: vi.fn() }))
vi.mock('./hooks/useClearCompletedMutation', () => ({
  useClearCompletedMutation: vi.fn(),
}))
vi.mock('./components/TodosHeader', () => ({
  TodosHeader: () => <h1>Tasks</h1>,
}))
vi.mock('./components/TodoSummary', () => ({
  TodoSummary: vi.fn(
    ({ onClearCompleted }: { onClearCompleted: () => void }) => (
      <button type="button" onClick={onClearCompleted}>
        Clear completed
      </button>
    ),
  ),
}))
vi.mock('./components/TodoFilters', () => ({ TodoFilters: () => null }))
vi.mock('./components/TodoList', () => ({ TodoList: () => <p>Task list</p> }))
vi.mock('./components/TodoEditor', () => ({ TodoEditor: () => null }))
vi.mock('./components/DeleteTodoDialog', () => ({
  DeleteTodoDialog: () => null,
}))
vi.mock('../../components/SuccessNotice', () => ({ SuccessNotice: () => null }))

beforeEach(() => vi.clearAllMocks())

function setup({
  busy = false,
  queryError = null as Error | null,
  clearError = null as Error | null,
  clearMutateAsync = vi.fn(),
} = {}) {
  const refetch = vi.fn().mockResolvedValue(undefined)
  const toggleReset = vi.fn()
  const clearReset = vi.fn()
  const notify = vi.fn()
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
    data: todoStatsFixture,
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
  return { refetch, toggleReset, clearReset, notify }
}

it('displays a query failure and resets mutation errors before retrying', async () => {
  const user = userEvent.setup()
  const { refetch, toggleReset, clearReset } = setup({
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

it('passes the loaded stats and busy state to the summary', () => {
  setup({ busy: true })
  expect(vi.mocked(TodoSummary).mock.lastCall?.[0]).toMatchObject({
    stats: todoStatsFixture,
    busy: true,
  })
})

it.each([
  [1, 'Cleared 1 completed task.'],
  [3, 'Cleared 3 completed tasks.'],
])(
  'announces how many completed tasks were cleared (%i)',
  async (deleted, notice) => {
    const user = userEvent.setup()
    const clearMutateAsync = vi.fn().mockResolvedValue({ deleted })
    const { notify } = setup({ clearMutateAsync })
    await user.click(screen.getByRole('button', { name: 'Clear completed' }))
    await waitFor(() => expect(notify).toHaveBeenCalledWith(notice))
    expect(clearMutateAsync).toHaveBeenCalledTimes(1)
  },
)

it('does not clear completed tasks while busy', async () => {
  const user = userEvent.setup()
  const clearMutateAsync = vi.fn()
  const { notify } = setup({ busy: true, clearMutateAsync })
  await user.click(screen.getByRole('button', { name: 'Clear completed' }))
  expect(clearMutateAsync).not.toHaveBeenCalled()
  expect(notify).not.toHaveBeenCalled()
})

it('shows a clear failure in the page alert without a notice', async () => {
  const user = userEvent.setup()
  const clearMutateAsync = vi.fn().mockRejectedValue(new Error('Clear failed'))
  const { notify } = setup({
    clearError: new Error('Could not clear completed tasks.'),
    clearMutateAsync,
  })
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'Could not clear completed tasks.',
  )
  await user.click(screen.getByRole('button', { name: 'Clear completed' }))
  await waitFor(() => expect(clearMutateAsync).toHaveBeenCalledTimes(1))
  expect(notify).not.toHaveBeenCalled()
})
