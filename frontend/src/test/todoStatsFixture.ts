import type { TodoStats } from '../features/todos/types'

export const todoStatsFixture: TodoStats = {
  total: 4,
  completed: 1,
  active: 3,
  overdue: 1,
  due_today: 2,
  active_by_priority: { low: 0, medium: 1, high: 2 },
  completion_rate: 0.25,
}
