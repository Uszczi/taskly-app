import type { TodoStats } from '../features/todos/types'

export const statsFixture: TodoStats = {
  total: 3,
  completed: 1,
  active: 2,
  overdue: 0,
  due_today: 0,
  active_by_priority: { low: 0, medium: 1, high: 1 },
  completion_rate: 0.33,
}
