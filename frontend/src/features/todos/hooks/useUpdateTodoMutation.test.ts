import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { statsFixture } from '../../../test/statsFixture'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('replaces the edited task in the list and marks the stats stale', async () => {
  const { client, wrapper } = createQueryWrapper()
  const other = { ...todoFixture, id: 8, title: 'Other task' }
  const saved = { ...todoFixture, completed: true }
  client.setQueryData(todoKeys.list, [todoFixture, other])
  client.setQueryData(todoKeys.stats, statsFixture)
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const { result } = renderHook(() => useUpdateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({ id: todoFixture.id, input: { completed: true } })
  })
  expect(todosApi.update).toHaveBeenCalledWith(todoFixture.id, { completed: true })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, other])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
