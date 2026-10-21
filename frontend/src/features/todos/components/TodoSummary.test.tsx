import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import type { TodoStats } from '../types'
import { TodoSummary } from './TodoSummary'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

const stats: TodoStats = {
  total: 4,
  completed: 1,
  active: 3,
  overdue: 1,
  due_today: 1,
  active_by_priority: { low: 1, medium: 0, high: 2 },
  completion_rate: 0.25,
}

it('renders nothing until statistics are loaded', () => {
  const { container } = render(
    <TodoSummary stats={undefined} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

it('shows progress, deadline pressure and open high-priority tasks', () => {
  render(<TodoSummary stats={stats} busy={false} onClearCompleted={vi.fn()} />)
  expect(
    screen.getByRole('region', { name: 'Task summary' }),
  ).toHaveTextContent('1 of 4 done (25%)')
  expect(screen.getByText('1 overdue · 1 due today')).toBeInTheDocument()
  expect(screen.getByText('2 high priority open')).toBeInTheDocument()
})

it('hides the deadline badge and high-priority line when neither applies', () => {
  render(
    <TodoSummary
      stats={{
        ...stats,
        overdue: 0,
        due_today: 0,
        active_by_priority: { low: 1, medium: 2, high: 0 },
      }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByText(/overdue|due today/)).not.toBeInTheDocument()
  expect(screen.queryByText(/high priority open/)).not.toBeInTheDocument()
})

it('offers to clear completed tasks with their count and forwards the click', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  render(
    <TodoSummary stats={stats} busy={false} onClearCompleted={onClearCompleted} />,
  )
  await user.click(
    screen.getByRole('button', { name: 'Clear completed (1)' }),
  )
  expect(onClearCompleted).toHaveBeenCalledTimes(1)
})

it('disables clearing while another change is in progress', () => {
  render(<TodoSummary stats={stats} busy onClearCompleted={vi.fn()} />)
  expect(
    screen.getByRole('button', { name: 'Clear completed (1)' }),
  ).toBeDisabled()
})

it('hides the clear action when no task is completed', () => {
  render(
    <TodoSummary
      stats={{ ...stats, completed: 0, active: 4 }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(
    screen.queryByRole('button', { name: /Clear completed/ }),
  ).not.toBeInTheDocument()
})
