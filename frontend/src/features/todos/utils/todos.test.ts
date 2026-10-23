import { describe, expect, it } from 'vitest'
import { describeDeadlines, describeProgress, selectTodos } from './todos'
import type { Todo, TodoStats } from '../types'

const stats: TodoStats = {
  total: 3,
  completed: 1,
  active: 2,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 0, medium: 2, high: 0 },
  completion_rate: 0.33,
}

describe('describeProgress', () => {
  it('handles empty, all-done and partial lists', () => {
    expect(describeProgress({ ...stats, total: 0, active: 0, completed: 0 })).toBe(
      'No tasks yet',
    )
    expect(describeProgress({ ...stats, active: 0, completed: 3 })).toBe(
      'All 3 tasks done',
    )
    expect(describeProgress(stats)).toBe('1 of 3 done (33%)')
  })
})

describe('describeDeadlines', () => {
  it('joins overdue and due-today counts, or returns null', () => {
    expect(describeDeadlines(stats)).toBeNull()
    expect(describeDeadlines({ ...stats, overdue: 2 })).toBe('2 overdue')
    expect(describeDeadlines({ ...stats, due_today: 1 })).toBe('1 due today')
    expect(describeDeadlines({ ...stats, overdue: 2, due_today: 1 })).toBe(
      '2 overdue · 1 due today',
    )
  })
})

const base: Todo = {
  id: 1,
  title: 'Sprint plan',
  description: '',
  priority: 'medium',
  completed: false,
  due_date: null,
  created_at: '2026-10-01T12:00:00Z',
  updated_at: '2026-10-01T12:00:00Z',
}

describe('selectTodos', () => {
  it('combines status with a case-insensitive search in the description', () => {
    const matching = { ...base, description: 'Discuss the API' }
    const todos = [
      matching,
      { ...matching, id: 2, completed: true },
      { ...base, id: 3 },
    ]
    expect(selectTodos(todos, 'active', ' api ', 'newest')).toEqual([matching])
  })

  it('sorts by priority without changing the source array', () => {
    const high: Todo = { ...base, id: 2, priority: 'high' }
    const todos = [base, high]
    expect(selectTodos(todos, 'all', '', 'priority')).toEqual([high, base])
    expect(todos).toEqual([base, high])
  })
})
