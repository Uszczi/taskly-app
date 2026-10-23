import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, expect, it, vi } from 'vitest'
import { useNotice } from '../../hooks/useNotice'
import { statsFixture } from '../../test/statsFixture'
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
vi.mock('./components/TodoFilters', () => ({ TodoFilters: () => null }))
vi.mock('./components/TodoList', () => ({ TodoList: () => <p>Task list</p> }))
vi.mock('./components/TodoEditor', () => ({ TodoEditor: () => null }))
vi.mock('./components/DeleteTodoDialog', () => ({
  DeleteTodoDialog: () => null,
}))
vi.mock('../../components/SuccessNotice', () => ({ SuccessNotice: () => null }))

const refetch = vi.fn()
const reset = vi.fn()
const clearReset = vi.fn()
const mutateClear = vi.fn()
const notify = vi.fn()

beforeEach(() => {
  vi.clearAllMocks()
  refetch.mockResolvedValue(undefined)
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: false,
    error: null,
    refetch,
  } as unknown as ReturnType<typeof useTodosQuery>)
  vi.mocked(useUpdateTodoMutation).mockReturnValue({
    error: null,
    reset,
    mutateAsync: vi.fn(),
  } as unknown as ReturnType<typeof useUpdateTodoMutation>)
  vi.mocked(useClearCompletedMutation).mockReturnValue({
    error: null,
    reset: clearReset,
    mutateAsync: mutateClear,
  } as unknown as ReturnType<typeof useClearCompletedMutation>)
  vi.mocked(useTodoStatsQuery).mockReturnValue({
    data: statsFixture,
  } as unknown as ReturnType<typeof useTodoStatsQuery>)
  vi.mocked(useTodosBusy).mockReturnValue(false)
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
})

it('displays a query failure and resets mutation errors before retrying', async () => {
  const user = userEvent.setup()
  vi.mocked(useTodosQuery).mockReturnValue({
    data: [],
    isPending: false,
    isFetching: false,
    isError: true,
    error: new Error('The server is unavailable.'),
    refetch,
  } as unknown as ReturnType<typeof useTodosQuery>)
  render(<TodosPage />)
  expect(screen.getByTestId('alert')).toHaveTextContent(
    'The server is unavailable.',
  )
  await user.click(screen.getByRole('button', { name: 'Try again' }))
  await waitFor(() => expect(refetch).toHaveBeenCalledTimes(1))
  expect(reset).toHaveBeenCalledTimes(1)
  expect(clearReset).toHaveBeenCalledTimes(1)
  expect(reset.mock.invocationCallOrder[0]).toBeLessThan(
    refetch.mock.invocationCallOrder[0],
  )
})

it('clears completed tasks and announces the plural count', async () => {
  const user = userEvent.setup()
  mutateClear.mockResolvedValue({ deleted: 3 })
  render(<TodosPage />)
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  expect(mutateClear).toHaveBeenCalledTimes(1)
  expect(notify).toHaveBeenCalledWith('Cleared 3 completed tasks.')
})

it('announces a singular count when one task was cleared', async () => {
  const user = userEvent.setup()
  mutateClear.mockResolvedValue({ deleted: 1 })
  render(<TodosPage />)
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  await waitFor(() =>
    expect(notify).toHaveBeenCalledWith('Cleared 1 completed task.'),
  )
})

it('shows the clear-completed failure in the alert without a notice', async () => {
  const user = userEvent.setup()
  mutateClear.mockRejectedValue(new Error('Could not clear.'))
  vi.mocked(useClearCompletedMutation).mockReturnValue({
    error: new Error('Could not clear.'),
    reset: clearReset,
    mutateAsync: mutateClear,
  } as unknown as ReturnType<typeof useClearCompletedMutation>)
  render(<TodosPage />)
  expect(screen.getByTestId('alert')).toHaveTextContent('Could not clear.')
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  expect(notify).not.toHaveBeenCalled()
})

it('does not clear completed tasks while busy', () => {
  vi.mocked(useTodosBusy).mockReturnValue(true)
  render(<TodosPage />)
  expect(
    screen.getByRole('button', { name: 'Clear completed (1)' }),
  ).toBeDisabled()
  expect(mutateClear).not.toHaveBeenCalled()
})
