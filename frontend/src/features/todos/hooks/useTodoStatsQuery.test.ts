import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { statsFixture } from '../../../test/statsFixture'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useTodoStatsQuery } from './useTodoStatsQuery'

vi.mock('../api/todos', () => ({ todosApi: { stats: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('loads stats with the abort signal and caches them under the stats key', async () => {
  vi.mocked(todosApi.stats).mockResolvedValue(statsFixture)
  const { client, wrapper } = createQueryWrapper()
  const { result } = renderHook(() => useTodoStatsQuery(), { wrapper })
  await waitFor(() => expect(result.current.data).toEqual(statsFixture))
  expect(todosApi.stats).toHaveBeenCalledWith(expect.any(AbortSignal))
  expect(client.getQueryData(todoKeys.stats)).toEqual(statsFixture)
})
