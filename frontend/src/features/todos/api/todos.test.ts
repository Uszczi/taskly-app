import { beforeEach, expect, it, vi } from 'vitest'
import { request } from '../../../lib/http'
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

it('fetches the task statistics with the abort signal', async () => {
  const signal = new AbortController().signal
  const stats = {
    total: 1,
    completed: 0,
    active: 1,
    overdue: 0,
    due_today: 0,
    active_by_priority: { low: 0, medium: 1, high: 0 },
    completion_rate: 0,
  }
  vi.mocked(request).mockResolvedValue(stats)
  await expect(todosApi.stats(signal)).resolves.toEqual(stats)
  expect(request).toHaveBeenCalledWith('/todos/stats', { signal })
})

it('deletes all completed tasks and returns the reported count', async () => {
  vi.mocked(request).mockResolvedValue({ deleted: 3 })
  await expect(todosApi.clearCompleted()).resolves.toEqual({ deleted: 3 })
  expect(request).toHaveBeenCalledWith('/todos/completed', { method: 'DELETE' })
})
