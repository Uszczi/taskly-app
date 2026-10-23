import { describe, expect, it } from 'vitest'
import { describeDeadlines, describeProgress, selectTodos } from './todos'
import type { Todo } from '../types'
import { statsFixture } from '../../../test/statsFixture'

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
  it('reports that there are no tasks yet when the list is empty', () => {
    expect(describeProgress({ ...statsFixture, total: 0, completed: 0, active: 0, completion_rate: 0 })).toBe('No tasks yet')
  })

  it('reports completion once every task is done', () => {
    expect(describeProgress({ ...statsFixture, completed: 3, active: 0, completion_rate: 1 })).toBe('All 3 tasks done')
  })

  it('reports completed tasks as a rounded percentage of the total', () => {
    expect(describeProgress(statsFixture)).toBe('1 of 3 done (33%)')
  })
})

describe('describeDeadlines', () => {
  it('returns null when no active task is overdue or due today', () => {
    expect(describeDeadlines(statsFixture)).toBeNull()
  })

  it('lists overdue and due-today counts separated by a dot', () => {
    expect(describeDeadlines({ ...statsFixture, overdue: 2, due_today: 1 })).toBe('2 overdue · 1 due today')
  })

  it('omits the category that has no tasks', () => {
    expect(describeDeadlines({ ...statsFixture, overdue: 2 })).toBe('2 overdue')
    expect(describeDeadlines({ ...statsFixture, due_today: 1 })).toBe('1 due today')
  })
})
