import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useClearCompletedMutation } from './useClearCompletedMutation'

vi.mock('../api/todos', () => ({ todosApi: { clearCompleted: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const finished: Todo = { ...todoFixture, id: 8, completed: true }
const open: Todo = { ...todoFixture, id: 9, completed: false }

it('removes completed tasks from the cached list and reports how many were deleted', async () => {
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData<Todo[]>(todoKeys.list, [finished, open])
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  let response: { deleted: number } | undefined
  await act(async () => {
    response = await result.current.mutateAsync()
  })
  expect(response).toEqual({ deleted: 1 })
  expect(todosApi.clearCompleted).toHaveBeenCalledTimes(1)
  expect(client.getQueryData<Todo[]>(todoKeys.list)).toEqual([open])
})

it('marks the cached statistics stale so they reload after clearing', async () => {
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  client.setQueryData<Todo[]>(todoKeys.list, [finished, open])
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync()
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('keeps the cached list unchanged when clearing fails', async () => {
  vi.mocked(todosApi.clearCompleted).mockRejectedValue(new Error('The server is unavailable.'))
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData<Todo[]>(todoKeys.list, [finished, open])
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await expect(result.current.mutateAsync()).rejects.toThrow('The server is unavailable.')
  })
  expect(result.current.error?.message).toBe('The server is unavailable.')
  expect(client.getQueryData<Todo[]>(todoKeys.list)).toEqual([finished, open])
})
