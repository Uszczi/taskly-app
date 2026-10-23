import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useDeleteTodoMutation } from './useDeleteTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { remove: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('removes the deleted task from the list and invalidates stats', async () => {
  const { client, wrapper } = createQueryWrapper()
  const keep = { ...todoFixture, id: 2 }
  const drop = { ...todoFixture, id: 3 }
  client.setQueryData(todoKeys.list, [keep, drop])
  client.setQueryData(todoKeys.stats, { total: 2 })
  vi.mocked(todosApi.remove).mockResolvedValue(undefined)
  const { result } = renderHook(() => useDeleteTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync(3)
  })
  expect(todosApi.remove).toHaveBeenCalledWith(3)
  expect(client.getQueryData(todoKeys.list)).toEqual([keep])
  await waitFor(() =>
    expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true),
  )
})
