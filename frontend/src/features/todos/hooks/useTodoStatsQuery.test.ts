import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todosApi } from '../api/todos'
import { useTodoStatsQuery } from './useTodoStatsQuery'

vi.mock('../api/todos', () => ({ todosApi: { stats: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('loads the task statistics from the stats endpoint', async () => {
  vi.mocked(todosApi.stats).mockResolvedValue(todoStatsFixture)
  const { wrapper } = createQueryWrapper()
  const { result } = renderHook(() => useTodoStatsQuery(), { wrapper })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toEqual(todoStatsFixture)
  expect(todosApi.stats).toHaveBeenCalledTimes(1)
})

it('passes the query abort signal to the stats request', async () => {
  vi.mocked(todosApi.stats).mockResolvedValue(todoStatsFixture)
  const { wrapper } = createQueryWrapper()
  const { result } = renderHook(() => useTodoStatsQuery(), { wrapper })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(vi.mocked(todosApi.stats).mock.calls[0][0]).toHaveProperty('aborted', false)
})
