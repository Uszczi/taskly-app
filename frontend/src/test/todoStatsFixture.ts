import type { TodoStats } from '../features/todos/types'

export const todoStatsFixture: TodoStats = {
  total: 4,
  completed: 1,
  active: 3,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 1, medium: 2, high: 0 },
  completion_rate: 0.25,
}
