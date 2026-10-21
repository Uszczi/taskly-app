import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, renderHook } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { TodoStats } from '../types'
import { useCreateTodoMutation } from './useCreateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const stats: TodoStats = {
  total: 0,
  completed: 0,
  active: 0,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 0, medium: 0, high: 0 },
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

it('prepends the saved task to the cached list', async () => {
  const older = { ...todoFixture, id: 1 }
  const { client, result } = renderWithClient(() => useCreateTodoMutation())
  client.setQueryData(todoKeys.list, [older])
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  await act(async () => {
    await result.current.mutateAsync({ ...todoFixture })
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture, older])
})

it('marks task statistics stale after a task is created', async () => {
  const { client, result } = renderWithClient(() => useCreateTodoMutation())
  client.setQueryData(todoKeys.stats, stats)
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  await act(async () => {
    await result.current.mutateAsync({ ...todoFixture })
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
