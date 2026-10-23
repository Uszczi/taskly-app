import { beforeEach, expect, it, vi } from 'vitest'
import { request } from '../../../lib/http'
import { statsFixture } from '../../../test/statsFixture'
import { todoFixture } from '../../../test/todoFixture'
import { todosApi } from './todos'

vi.mock('../../../lib/http', () => ({ request: vi.fn() }))
beforeEach(() => vi.clearAllMocks())

it('passes the abort signal when fetching tasks', async () => {
  const signal = new AbortController().signal
  vi.mocked(request).mockResolvedValue([todoFixture])
  await expect(todosApi.list(signal)).resolves.toEqual([todoFixture])
  expect(request).toHaveBeenCalledWith('/todos', { signal })
})

it('sends only writable task fields on creation', async () => {
  vi.mocked(request).mockResolvedValue(todoFixture)
  await expect(todosApi.create(todoFixture)).resolves.toEqual(todoFixture)
  expect(request).toHaveBeenCalledWith('/todos', {
    method: 'POST',
    body: JSON.stringify({
      title: todoFixture.title,
      description: '',
      priority: 'medium',
      due_date: null,
      completed: false,
    }),
  })
})

it('requests task statistics with the abort signal', async () => {
  const signal = new AbortController().signal
  vi.mocked(request).mockResolvedValue(statsFixture)
  await expect(todosApi.stats(signal)).resolves.toEqual(statsFixture)
  expect(request).toHaveBeenCalledWith('/todos/stats', { signal })
})

it('deletes completed tasks in one request and returns the count', async () => {
  vi.mocked(request).mockResolvedValue({ deleted: 2 })
  await expect(todosApi.clearCompleted()).resolves.toEqual({ deleted: 2 })
  expect(request).toHaveBeenCalledWith('/todos/completed', { method: 'DELETE' })
})
