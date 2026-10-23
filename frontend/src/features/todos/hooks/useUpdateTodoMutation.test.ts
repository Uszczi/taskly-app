import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const other: Todo = { ...todoFixture, id: 3, title: 'Book travel' }

it('replaces the updated task in the cached list and keeps the others', async () => {
  const saved: Todo = { ...todoFixture, completed: true }
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData<Todo[]>(todoKeys.list, [other, todoFixture])
  const { result } = renderHook(() => useUpdateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({ id: todoFixture.id, input: { completed: true } })
  })
  expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, { completed: true })
  expect(client.getQueryData<Todo[]>(todoKeys.list)).toEqual([other, saved])
})

it('marks the cached statistics stale after a task is updated', async () => {
  vi.mocked(todosApi.update).mockResolvedValue({ ...todoFixture, completed: true })
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  client.setQueryData<Todo[]>(todoKeys.list, [todoFixture])
  const { result } = renderHook(() => useUpdateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({ id: todoFixture.id, input: { completed: true } })
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
