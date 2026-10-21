import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import {
  formatDate,
  isOverdue,
  selectTodos,
  validateTodo,
} from './todos'
import type { Todo, TodoInput } from '../types'

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

const input: TodoInput = {
  title: 'Write report',
  description: '',
  priority: 'low',
  due_date: null,
  completed: false,
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 15, 12))
})

afterEach(() => {
  vi.useRealTimers()
})

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

  it('sorts by due date with undated tasks last and ties broken by newest id', () => {
    const undated: Todo = { ...base, id: 5, due_date: null }
    const laterSameDay: Todo = { ...base, id: 4, due_date: '2026-10-20' }
    const earlierSameDay: Todo = { ...base, id: 3, due_date: '2026-10-20' }
    const soonest: Todo = { ...base, id: 2, due_date: '2026-10-02' }
    const result = selectTodos(
      [undated, earlierSameDay, soonest, laterSameDay],
      'all',
      '',
      'due',
    )
    expect(result.map((todo) => todo.id)).toEqual([2, 4, 3, 5])
  })

  it('sorts newest first by creation time and ties broken by newest id', () => {
    const older: Todo = { ...base, id: 1, created_at: '2026-10-01T09:00:00Z' }
    const newer: Todo = { ...base, id: 2, created_at: '2026-10-03T09:00:00Z' }
    const sameTimeHigherId: Todo = { ...base, id: 3, created_at: '2026-10-01T09:00:00Z' }
    const result = selectTodos([older, newer, sameTimeHigherId], 'all', '', 'newest')
    expect(result.map((todo) => todo.id)).toEqual([2, 3, 1])
  })
})

describe('validateTodo', () => {
  it('returns no errors for a valid input', () => {
    expect(validateTodo({ ...input, due_date: '2026-02-28' })).toEqual({})
  })

  it('requires a non-blank title', () => {
    expect(validateTodo({ ...input, title: '   ' })).toEqual({
      title: 'Enter a task title.',
    })
  })

  it('rejects titles longer than 120 characters after trimming', () => {
    expect(validateTodo({ ...input, title: ` ${'a'.repeat(121)} ` })).toEqual({
      title: 'The title must be at most 120 characters.',
    })
    expect(validateTodo({ ...input, title: 'a'.repeat(120) })).toEqual({})
  })

  it('rejects descriptions longer than 2000 characters', () => {
    expect(validateTodo({ ...input, description: 'a'.repeat(2001) })).toEqual({
      description: 'The description must be at most 2000 characters.',
    })
  })

  it('rejects dates that do not exist or are not in YYYY-MM-DD form', () => {
    expect(validateTodo({ ...input, due_date: '2026-02-30' })).toEqual({
      due_date: 'Enter a valid date.',
    })
    expect(validateTodo({ ...input, due_date: '2026-1-5' })).toEqual({
      due_date: 'Enter a valid date.',
    })
  })
})

describe('isOverdue', () => {
  it('is true for an open task whose due date is before today', () => {
    expect(isOverdue({ ...base, due_date: '2026-10-14' })).toBe(true)
  })

  it('is false when the due date is today or undated', () => {
    expect(isOverdue({ ...base, due_date: '2026-10-15' })).toBe(false)
    expect(isOverdue({ ...base, due_date: null })).toBe(false)
  })

  it('is false for a completed task even if its due date has passed', () => {
    expect(isOverdue({ ...base, completed: true, due_date: '2026-10-01' })).toBe(
      false,
    )
  })
})

describe('formatDate', () => {
  it('formats an ISO date as day, short month and year in British English', () => {
    expect(formatDate('2026-10-05')).toBe('5 Oct 2026')
  })
})
