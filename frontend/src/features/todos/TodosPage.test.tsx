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
vi.mock('./components/TodoSummary', () => ({
  TodoSummary: ({
    stats,
    busy,
    onClearCompleted,
  }: {
    stats?: { total: number }
    busy: boolean
    onClearCompleted: () => void
  }) => (
    <button type="button" onClick={onClearCompleted}>
      Summary {stats?.total} {busy ? 'busy' : 'idle'}
    </button>
  ),
}))
vi.mock('./components/TodoFilters', () => ({ TodoFilters: () => null }))
vi.mock('./components/TodoList', () => ({ TodoList: () => <p>Task list</p> }))
vi.mock('./components/TodoEditor', () => ({ TodoEditor: () => null }))
vi.mock('./components/DeleteTodoDialog', () => ({
  DeleteTodoDialog: () => null,
}))
vi.mock('../../components/SuccessNotice', () => ({ SuccessNotice: () => null }))

const notify = vi.fn()
const toggleReset = vi.fn()
const clearReset = vi.fn()
const refetch = vi.fn().mockResolvedValue(undefined)
const clearMutate = vi.fn()

function setup({
  queryError = null,
  clearError = null,
  busy = false,
}: {
  queryError?: Error | null
  clearError?: Error | null
  busy?: boolean
} = {}) {
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: !!queryError,
    error: queryError,
    refetch,
  } as unknown as ReturnType<typeof useTodosQuery>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    error: null,
    reset: toggleReset,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  vi.mocked(useClearCompletedMutation).mockReturnValue({
    error: clearError,
    reset: clearReset,
    mutateAsync: clearMutate,
  } as unknown as ReturnType<typeof useClearCompletedMutation>)
  vi.mocked(useTodoStatsQuery).mockReturnValue({
    data: { total: 5 },
  } as unknown as ReturnType<typeof useTodoStatsQuery>)
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
}

beforeEach(() => vi.clearAllMocks())

it('displays a query failure and resets mutation errors before retrying', async () => {
  const user = userEvent.setup()
  setup({ queryError: new Error('The server is unavailable.') })
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1))
  expect(toggleReset).toHaveBeenCalledTimes(1)
  expect(clearReset).toHaveBeenCalledTimes(1)
  expect(clearReset.mock.invocationCallOrder[0]).toBeLessThan(
    refetch.mock.invocationCallOrder[0],
  )
})

it('passes stats and busy state to the summary', () => {
  setup({ busy: true })
  expect(screen.getByRole('button', { name: 'Summary 5 busy' })).toBeInTheDocument()
})

it.each([
  [1, 'Cleared 1 completed task.'],
  [3, 'Cleared 3 completed tasks.'],
])('announces clearing %i completed tasks', async (deleted, message) => {
  const user = userEvent.setup()
  clearMutate.mockResolvedValue({ deleted })
  setup()
  await user.click(screen.getByRole('button', { name: /Summary/ }))
  await waitFor(() => expect(notify).toHaveBeenCalledWith(message))
})

it('does not clear completed tasks while busy', async () => {
  const user = userEvent.setup()
  setup({ busy: true })
  await user.click(screen.getByRole('button', { name: /Summary/ }))
  expect(clearMutate).not.toHaveBeenCalled()
})

it('shows the clear failure in the alert without a notice', async () => {
  const user = userEvent.setup()
  clearMutate.mockRejectedValue(new Error('Could not clear.'))
  setup({ clearError: new Error('Could not clear.') })
  await user.click(screen.getByRole('button', { name: /Summary/ }))
  expect(screen.getByTestId('alert')).toHaveTextContent('Could not clear.')
  expect(notify).not.toHaveBeenCalled()
})
