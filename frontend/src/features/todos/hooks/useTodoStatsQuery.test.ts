import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import { createElement, type ReactNode } from 'react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todosApi } from '../api/todos'
import type { TodoStats } from '../types'
import { useTodoStatsQuery } from './useTodoStatsQuery'

vi.mock('../api/todos', () => ({ todosApi: { stats: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const stats: TodoStats = {
  total: 2,
  completed: 1,
  active: 1,
  overdue: 0,
  due_today: 1,
  active_by_priority: { low: 0, medium: 1, high: 0 },
  completion_rate: 0.5,
}

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return createElement(QueryClientProvider, { client }, children)
}

it('loads task statistics through the stats endpoint with the query signal', async () => {
  vi.mocked(todosApi.stats).mockResolvedValue(stats)
  const { result } = renderHook(() => useTodoStatsQuery(), { wrapper })
  await waitFor(() => expect(result.current.data).toEqual(stats))
  expect(todosApi.stats).toHaveBeenCalledWith(expect.any(AbortSignal))
})
