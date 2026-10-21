import { describe, expect, it } from 'vitest'
import {
  describeDeadlines,
  describeProgress,
  selectTodos,
} from './todos'
import type { Todo, TodoStats } from '../types'

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

const emptyStats: TodoStats = {
  total: 0,
  completed: 0,
  active: 0,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 0, medium: 0, high: 0 },
  completion_rate: 0,
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

describe('describeProgress', () => {
  it('says there are no tasks when the list is empty', () => {
    expect(describeProgress(emptyStats)).toBe('No tasks yet')
  })

  it('says every task is done when none are active', () => {
    expect(
      describeProgress({ ...emptyStats, total: 3, completed: 3, completion_rate: 1 }),
    ).toBe('All 3 tasks done')
  })

  it('reports completed count and rounded completion percentage', () => {
    expect(
      describeProgress({
        ...emptyStats,
        total: 3,
        completed: 1,
        active: 2,
        completion_rate: 0.33,
      }),
    ).toBe('1 of 3 done (33%)')
  })
})

describe('describeDeadlines', () => {
  it('returns null when nothing is overdue or due today', () => {
    expect(describeDeadlines({ ...emptyStats, active: 2 })).toBeNull()
  })

  it('lists overdue and due-today counts separated by a middle dot', () => {
    expect(
      describeDeadlines({ ...emptyStats, active: 3, overdue: 2, due_today: 1 }),
    ).toBe('2 overdue · 1 due today')
  })

  it('omits the overdue part when only tasks are due today', () => {
    expect(describeDeadlines({ ...emptyStats, active: 1, due_today: 1 })).toBe(
      '1 due today',
    )
  })
})
