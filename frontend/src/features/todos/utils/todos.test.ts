import { describe, expect, it } from 'vitest'
import { describeDeadlines, describeProgress, selectTodos } from './todos'
import type { Todo } from '../types'
import { todoStatsFixture } from '../../../test/todoStatsFixture'

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

describe('describeProgress', () => {
  it('reports the share of completed tasks as a rounded percentage', () => {
    expect(describeProgress(todoStatsFixture)).toBe('1 of 4 done (25%)')
    expect(
      describeProgress({ ...todoStatsFixture, completed: 2, active: 2, completion_rate: 0.67 }),
    ).toBe('2 of 4 done (67%)')
  })

  it('says there are no tasks when the list is empty', () => {
    expect(
      describeProgress({ ...todoStatsFixture, total: 0, completed: 0, active: 0, completion_rate: 0 }),
    ).toBe('No tasks yet')
  })

  it('says everything is done when no task is active', () => {
    expect(
      describeProgress({ ...todoStatsFixture, completed: 4, active: 0, completion_rate: 1 }),
    ).toBe('All 4 tasks done')
  })
})

describe('describeDeadlines', () => {
  it('returns null when no active task is overdue or due today', () => {
    expect(describeDeadlines({ ...todoStatsFixture, overdue: 0, due_today: 0 })).toBeNull()
  })

  it('describes overdue and due-today counts separated by a middle dot', () => {
    expect(describeDeadlines(todoStatsFixture)).toBe('1 overdue · 2 due today')
  })

  it('omits the count that is zero', () => {
    expect(describeDeadlines({ ...todoStatsFixture, due_today: 0 })).toBe('1 overdue')
    expect(describeDeadlines({ ...todoStatsFixture, overdue: 0 })).toBe('2 due today')
  })
})
