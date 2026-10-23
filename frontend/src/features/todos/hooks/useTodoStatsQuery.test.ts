import { renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { statsFixture } from '../../../test/statsFixture'
import { todosApi } from '../api/todos'
import { useTodoStatsQuery } from './useTodoStatsQuery'

vi.mock('../api/todos', () => ({ todosApi: { stats: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('loads task statistics through the API with the query signal', async () => {
  const { wrapper } = createQueryWrapper()
  vi.mocked(todosApi.stats).mockResolvedValue(statsFixture)
  const { result } = renderHook(() => useTodoStatsQuery(), { wrapper })
  await waitFor(() => expect(result.current.data).toEqual(statsFixture))
  expect(todosApi.stats).toHaveBeenCalledWith(expect.any(AbortSignal))
})
