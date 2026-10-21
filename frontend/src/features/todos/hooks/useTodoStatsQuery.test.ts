import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useTodoStatsQuery } from './useTodoStatsQuery'

vi.mock('../api/todos', () => ({ todosApi: { stats: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('fetches the stats with an abort signal and caches them under the stats key', async () => {
  const { client, wrapper } = createQueryWrapper()
  vi.mocked(todosApi.stats).mockResolvedValue(todoStatsFixture)
  const { result } = renderHook(() => useTodoStatsQuery(), { wrapper })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toEqual(todoStatsFixture)
  expect(todosApi.stats).toHaveBeenCalledTimes(1)
  expect(vi.mocked(todosApi.stats).mock.calls[0][0]).toBeInstanceOf(AbortSignal)
  expect(client.getQueryData(todoKeys.stats)).toEqual(todoStatsFixture)
})
