import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useClearCompletedMutation } from './useClearCompletedMutation'

vi.mock('../api/todos', () => ({ todosApi: { clearCompleted: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('drops completed tasks from the cached list and marks the stats stale', async () => {
  const { client, wrapper } = createQueryWrapper()
  const active = { ...todoFixture, id: 1 }
  const done = { ...todoFixture, id: 2, completed: true }
  client.setQueryData(todoKeys.list, [active, done])
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  const response = await act(() => result.current.mutateAsync())
  expect(response).toEqual({ deleted: 1 })
  expect(todosApi.clearCompleted).toHaveBeenCalledTimes(1)
  expect(client.getQueryData(todoKeys.list)).toEqual([active])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('leaves the cache untouched when clearing fails', async () => {
  const { client, wrapper } = createQueryWrapper()
  const done = { ...todoFixture, completed: true }
  client.setQueryData(todoKeys.list, [done])
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  vi.mocked(todosApi.clearCompleted).mockRejectedValue(new Error('Server down'))
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(() =>
    expect(result.current.mutateAsync()).rejects.toThrow('Server down'),
  )
  expect(client.getQueryData(todoKeys.list)).toEqual([done])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(false)
})
