import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('replaces the task in the list and invalidates stats', async () => {
  const saved = { ...todoFixture, completed: true }
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const { client, wrapper } = createQueryWrapper()
  const other = { ...todoFixture, id: 9 }
  client.setQueryData(todoKeys.list, [todoFixture, other])
  client.setQueryData(todoKeys.stats, {})
  const { result } = renderHook(() => useUpdateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({
      id: todoFixture.id,
      input: { completed: true },
    })
  })
  expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, {
    completed: true,
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, other])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
