import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { statsFixture } from '../../../test/statsFixture'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { remove: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('removes the deleted task from the list and marks the stats stale', async () => {
  const { client, wrapper } = createQueryWrapper()
  const other = { ...todoFixture, id: 8 }
  client.setQueryData(todoKeys.list, [todoFixture, other])
  client.setQueryData(todoKeys.stats, statsFixture)
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { result } = renderHook(() => useDeleteTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync(todoFixture.id)
  })
  expect(todosApi.remove).toHaveBeenCalledWith(todoFixture.id)
  expect(client.getQueryData(todoKeys.list)).toEqual([other])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
