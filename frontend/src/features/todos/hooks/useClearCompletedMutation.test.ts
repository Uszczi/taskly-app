import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { statsFixture } from '../../../test/statsFixture'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useClearCompletedMutation } from './useClearCompletedMutation'

vi.mock('../api/todos', () => ({ todosApi: { clearCompleted: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('removes completed tasks from the list and marks the stats stale', async () => {
  const { client, wrapper } = createQueryWrapper()
  const completed = { ...todoFixture, id: 8, completed: true }
  client.setQueryData(todoKeys.list, [todoFixture, completed])
  client.setQueryData(todoKeys.stats, statsFixture)
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await expect(result.current.mutateAsync()).resolves.toEqual({ deleted: 1 })
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('leaves the cached list unchanged when the server rejects the request', async () => {
  const { client, wrapper } = createQueryWrapper()
  const completed = { ...todoFixture, id: 8, completed: true }
  client.setQueryData(todoKeys.list, [todoFixture, completed])
  vi.mocked(todosApi.clearCompleted).mockRejectedValue(new Error('The server is unavailable.'))
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await expect(result.current.mutateAsync()).rejects.toThrow('The server is unavailable.')
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture, completed])
})
