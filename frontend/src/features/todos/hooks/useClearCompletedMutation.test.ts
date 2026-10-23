import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useClearCompletedMutation } from './useClearCompletedMutation'

vi.mock('../api/todos', () => ({ todosApi: { clearCompleted: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('drops completed tasks from the cached list and invalidates stats', async () => {
  vi.mocked(todosApi.clearCompleted).mockResolvedValue({ deleted: 1 })
  const { client, wrapper } = createQueryWrapper()
  const active = todoFixture
  const done = { ...todoFixture, id: 8, completed: true }
  client.setQueryData(todoKeys.list, [active, done])
  client.setQueryData(todoKeys.stats, {})
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  let response
  await act(async () => {
    response = await result.current.mutateAsync()
  })
  expect(response).toEqual({ deleted: 1 })
  expect(client.getQueryData(todoKeys.list)).toEqual([active])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('keeps the cached list when clearing fails', async () => {
  vi.mocked(todosApi.clearCompleted).mockRejectedValue(new Error('nope'))
  const { client, wrapper } = createQueryWrapper()
  const done = { ...todoFixture, completed: true }
  client.setQueryData(todoKeys.list, [done])
  const { result } = renderHook(() => useClearCompletedMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync().catch(() => undefined)
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([done])
})
