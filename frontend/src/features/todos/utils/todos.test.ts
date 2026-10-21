import { describe, expect, it } from 'vitest'
import { describeDeadlines, describeProgress, selectTodos } from './todos'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import type { Todo } from '../types'

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
  it('says there are no tasks when the list is empty', () => {
    const stats = { ...todoStatsFixture, total: 0, completed: 0, active: 0 }
    expect(describeProgress(stats)).toBe('No tasks yet')
  })

  it('says all tasks are done when none is active', () => {
    const stats = { ...todoStatsFixture, completed: 4, active: 0, completion_rate: 1 }
    expect(describeProgress(stats)).toBe('All 4 tasks done')
  })

  it('shows done of total with a rounded percentage', () => {
    const stats = { ...todoStatsFixture, total: 3, completed: 2, active: 1, completion_rate: 0.67 }
    expect(describeProgress(stats)).toBe('2 of 3 done (67%)')
  })
})

describe('describeDeadlines', () => {
  it('returns null when nothing is overdue or due today', () => {
    expect(describeDeadlines(todoStatsFixture)).toBeNull()
  })

  it('lists only the deadline counts that are nonzero', () => {
    expect(describeDeadlines({ ...todoStatsFixture, overdue: 2 })).toBe('2 overdue')
    expect(describeDeadlines({ ...todoStatsFixture, due_today: 1 })).toBe('1 due today')
  })

  it('joins overdue and due today with a middle dot', () => {
    expect(describeDeadlines({ ...todoStatsFixture, overdue: 2, due_today: 1 })).toBe(
      '2 overdue · 1 due today',
    )
  })
})
