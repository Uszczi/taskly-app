import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { statsFixture } from '../../../test/statsFixture'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useCreateTodoMutation } from './useCreateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('puts the saved task first and marks the stats stale', async () => {
  const { client, wrapper } = createQueryWrapper()
  const saved = { ...todoFixture, id: 9, title: 'Newest task' }
  client.setQueryData(todoKeys.list, [todoFixture])
  client.setQueryData(todoKeys.stats, statsFixture)
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync(todoFixture)
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, todoFixture])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('keeps the stats fresh when the create request fails', async () => {
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData(todoKeys.stats, statsFixture)
  vi.mocked(todosApi.create).mockRejectedValue(new Error('Validation failed.'))
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await expect(result.current.mutateAsync(todoFixture)).rejects.toThrow('Validation failed.')
  })
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(false)
})
