import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { TodoStats } from '../types'
import { useClearCompletedMutation } from './useClearCompletedMutation'

vi.mock('../api/todos', () => ({ todosApi: { clearCompleted: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const stats: TodoStats = {
  total: 2,
  completed: 1,
  active: 1,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 0, medium: 1, high: 0 },
  completion_rate: 0.5,
}

function renderWithClient<T>(hook: () => T) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  function wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children)
  }
  return { client, ...renderHook(hook, { wrapper }) }
}

const completed = { ...todoFixture, id: 3, completed: true }
const active = { ...todoFixture, id: 4, completed: false }

it('removes completed tasks from the cached list and reports the count', async () => {
  const { client, result } = renderWithClient(() => useClearCompletedMutation())
  client.setQueryData(todoKeys.list, [completed, active])
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  let response: { deleted: number } | undefined
  await act(async () => {
    response = await result.current.mutateAsync()
  })
  expect(todosApi.clearCompleted).toHaveBeenCalledTimes(1)
  expect(response).toEqual({ deleted: 1 })
  expect(client.getQueryData(todoKeys.list)).toEqual([active])
})

it('marks task statistics stale after completed tasks are cleared', async () => {
  const { client, result } = renderWithClient(() => useClearCompletedMutation())
  client.setQueryData(todoKeys.stats, stats)
  client.setQueryData(todoKeys.list, [completed, active])
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  await act(async () => {
    await result.current.mutateAsync()
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('keeps the cached list unchanged when clearing fails', async () => {
  const { client, result } = renderWithClient(() => useClearCompletedMutation())
  client.setQueryData(todoKeys.list, [completed, active])
  vi.mocked(todosApi.clearCompleted).mockRejectedValue(new Error('The server is unavailable.'))
  await act(async () => {
    await expect(result.current.mutateAsync()).rejects.toThrow('The server is unavailable.')
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([completed, active])
})
