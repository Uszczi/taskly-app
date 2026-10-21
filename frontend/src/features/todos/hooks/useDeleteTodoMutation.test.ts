import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { TodoStats } from '../types'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { remove: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const stats: TodoStats = {
  total: 1,
  completed: 0,
  active: 1,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 0, medium: 1, high: 0 },
  completion_rate: 0,
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

it('removes the deleted task from the cached list', async () => {
  const other = { ...todoFixture, id: 8 }
  const { client, result } = renderWithClient(() => useDeleteTodoMutation())
  client.setQueryData(todoKeys.list, [todoFixture, other])
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  await act(async () => {
    await result.current.mutateAsync(todoFixture.id)
  })
  expect(todosApi.remove).toHaveBeenCalledWith(todoFixture.id)
  expect(client.getQueryData(todoKeys.list)).toEqual([other])
})

it('marks task statistics stale after a task is deleted', async () => {
  const { client, result } = renderWithClient(() => useDeleteTodoMutation())
  client.setQueryData(todoKeys.stats, stats)
  client.setQueryData(todoKeys.list, [todoFixture])
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  await act(async () => {
    await result.current.mutateAsync(todoFixture.id)
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
