import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useUpdateTodoMutation } from './useUpdateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { update: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('replaces the updated task in the list and invalidates stats', async () => {
  const { client, wrapper } = createQueryWrapper()
  const other = { ...todoFixture, id: 2 }
  const saved = { ...todoFixture, id: 3, completed: true }
  client.setQueryData(todoKeys.list, [other, { ...saved, completed: false }])
  client.setQueryData(todoKeys.stats, { total: 2 })
  vi.mocked(todosApi.update).mockResolvedValue(saved)
  const { result } = renderHook(() => useUpdateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync({ id: 3, input: { completed: true } })
  })
  expect(todosApi.update).toHaveBeenCalledWith(3, { completed: true })
  expect(client.getQueryData(todoKeys.list)).toEqual([other, saved])
  await waitFor(() =>
    expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true),
  )
})
