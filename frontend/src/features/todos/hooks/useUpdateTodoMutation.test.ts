import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { TodoStats } from '../types'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))
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

it('replaces the updated task in the cached list', async () => {
  const saved = { ...todoFixture, completed: true }
  const { client, result } = renderWithClient(() => useUpdateTodoMutation())
  client.setQueryData(todoKeys.list, [todoFixture])
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  await act(async () => {
    await result.current.mutateAsync({ id: todoFixture.id, input: { completed: true } })
  })
  expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, { completed: true })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved])
})

it('marks task statistics stale after a task is updated', async () => {
  const { client, result } = renderWithClient(() => useUpdateTodoMutation())
  client.setQueryData(todoKeys.stats, stats)
  client.setQueryData(todoKeys.list, [todoFixture])
  vi.mocked(todosApi.update).mockResolvedValue({ ...todoFixture, completed: true })
  await act(async () => {
    await result.current.mutateAsync({ id: todoFixture.id, input: { completed: true } })
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
