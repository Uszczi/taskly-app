import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useCreateTodoMutation } from './useCreateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('prepends the created task and marks the stats stale', async () => {
  const { client, wrapper } = createQueryWrapper()
  const existing = { ...todoFixture, id: 1 }
  const saved = { ...todoFixture, id: 2 }
  client.setQueryData(todoKeys.list, [existing])
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(() => result.current.mutateAsync(saved))
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, existing])
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true)
})

it('keeps the stats fresh when creation fails', async () => {
  const { client, wrapper } = createQueryWrapper()
  client.setQueryData(todoKeys.stats, todoStatsFixture)
  vi.mocked(todosApi.create).mockRejectedValue(new Error('Server down'))
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(() =>
    expect(result.current.mutateAsync(todoFixture)).rejects.toThrow(
      'Server down',
    ),
  )
  expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(false)
})
