import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useClearCompletedMutation } from './useClearCompletedMutation'

vi.mock('../api/todos', () => ({ todosApi: { clearCompleted: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('removes completed tasks from the cached list and invalidates stats', async () => {
  const { client, wrapper } = createQueryWrapper()
  const done = { ...todoFixture, id: 2, completed: true }
  const open = { ...todoFixture, id: 3, completed: false }
  client.setQueryData(todoKeys.list, [done, open])
  client.setQueryData(todoKeys.stats, { total: 2 })
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync()
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([open])
  await waitFor(() =>
    expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true),
  )
})

it('keeps the cache untouched when clearing fails', async () => {
  const { client, wrapper } = createQueryWrapper()
  const done = { ...todoFixture, completed: true }
  client.setQueryData(todoKeys.list, [done])
  vi.mocked(todosApi.clearCompleted).mockRejectedValue(new Error('boom'))
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync().catch(() => undefined)
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([done])
})
