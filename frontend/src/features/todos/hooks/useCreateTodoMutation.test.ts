import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, expect, it, vi } from 'vitest'
import { createQueryWrapper } from '../../../test/queryClient'
import { todoFixture } from '../../../test/todoFixture'
import { todoKeys } from '../api/queryKeys'
import { todosApi } from '../api/todos'
import { useCreateTodoMutation } from './useCreateTodoMutation'

vi.mock('../api/todos', () => ({ todosApi: { create: vi.fn() } }))
beforeEach(() => vi.clearAllMocks())

it('prepends the created task and invalidates stats', async () => {
  const { client, wrapper } = createQueryWrapper()
  const existing = { ...todoFixture, id: 99 }
  const saved = { ...todoFixture, id: 100 }
  client.setQueryData(todoKeys.list, [existing])
  client.setQueryData(todoKeys.stats, { total: 1 })
  vi.mocked(todosApi.create).mockResolvedValue(saved)
  const { result } = renderHook(() => useCreateTodoMutation(), { wrapper })
  await act(async () => {
    await result.current.mutateAsync(saved)
  })
  expect(client.getQueryData(todoKeys.list)).toEqual([saved, existing])
  await waitFor(() =>
    expect(client.getQueryState(todoKeys.stats)?.isInvalidated).toBe(true),
  )
})
