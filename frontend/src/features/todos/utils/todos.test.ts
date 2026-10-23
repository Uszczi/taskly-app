import { describe, expect, it } from 'vitest'
import { describeDeadlines, describeProgress, selectTodos } from './todos'
import { statsFixture } from '../../../test/statsFixture'
import type { Todo } from '../types'

describe('describeProgress', () => {
  it('describes an empty list, a finished list and partial progress', () => {
    expect(describeProgress({ ...statsFixture, total: 0, active: 0 })).toBe(
      'No tasks yet',
    )
    expect(
      describeProgress({ ...statsFixture, total: 3, completed: 3, active: 0 }),
    ).toBe('All 3 tasks done')
    expect(describeProgress({ ...statsFixture, completion_rate: 0.33 })).toBe(
      '1 of 4 done (33%)',
    )
  })
})

describe('describeDeadlines', () => {
  it('joins overdue and due-today counts, skipping zeros', () => {
    expect(describeDeadlines(statsFixture)).toBeNull()
    expect(describeDeadlines({ ...statsFixture, overdue: 2 })).toBe('2 overdue')
    expect(describeDeadlines({ ...statsFixture, due_today: 1 })).toBe(
      '1 due today',
    )
    expect(
      describeDeadlines({ ...statsFixture, overdue: 2, due_today: 1 }),
    ).toBe('2 overdue · 1 due today')
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
