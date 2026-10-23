import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useCreateTodoMutation } from './useCreateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('prepends the saved task to the list and invalidates stats', async () => {
  vi.mocked(todosApi.create).mockResolvedValue(todoFixture)
  const { client, wrapper } = createQueryWrapper()
  const other = { ...todoFixture, id: 9 }
  client.setQueryData(todoKeys.list, [other])
  client.setQueryData(todoKeys.stats, {})
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync(todoFixture)
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([todoFixture, other])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})
