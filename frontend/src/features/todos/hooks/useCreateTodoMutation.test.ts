import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import type { Todo } from '../types'
import { useCreateTodoMutation } from './useCreateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

const created: Todo = { ...todoFixture, id: 8, title: 'Write the report' }
const existing: Todo = { ...todoFixture, id: 3, title: 'Book travel' }

it('puts the saved task at the top of the cached list', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(created)
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData<Todo[]>(todoKeys.list, [existing])
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({
      title: 'Write the report',
      description: '',
      priority: 'medium',
      due_date: null,
      completed: false,
    })
  })
  expect(todosApi.create).toHaveBeenCalledTimes(1)
  expect(client.getQueryData<Todo[]>(todoKeys.list)).toEqual([created, existing])
})

it('does not duplicate a task that is already cached when the server returns it', async () => {
  vi.mocked(todosApi.create).mockResolvedValue({ ...created, title: 'Saved title' })
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData<Todo[]>(todoKeys.list, [existing, created])
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({
      title: 'Saved title',
      description: '',
      priority: 'medium',
      due_date: null,
      completed: false,
    })
  })
  expect(client.getQueryData<Todo[]>(todoKeys.list)).toEqual([
    { ...created, title: 'Saved title' },
    existing,
  ])
})

it('marks the cached statistics stale after a task is created', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(created)
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({
      title: created.title,
      description: '',
      priority: 'medium',
      due_date: null,
      completed: false,
    })
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
