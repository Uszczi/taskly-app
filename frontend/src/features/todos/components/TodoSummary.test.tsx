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
  overdue: 2,
  due_today: 1,
  active_by_priority: { low: 0, medium: 1, high: 2 },
  completion_rate: 0.25,
}

it('renders nothing while stats are unavailable', () => {
  const { container } = render(
    <TodoSummary stats={undefined} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

it('shows progress, deadlines and high priority count', () => {
  render(<TodoSummary stats={stats} busy={false} onClearCompleted={vi.fn()} />)
  expect(screen.getByText('1 of 4 done (25%)')).toBeInTheDocument()
  expect(screen.getByText('2 overdue · 1 due today')).toBeInTheDocument()
  expect(screen.getByText('2 high priority open')).toBeInTheDocument()
})

it('hides deadlines, high priority and clear button when nothing applies', () => {
  render(
    <TodoSummary
      stats={{
        ...stats,
        completed: 0,
        overdue: 0,
        due_today: 0,
        active_by_priority: { low: 1, medium: 1, high: 0 },
      }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByText(/overdue|due today/)).not.toBeInTheDocument()
  expect(screen.queryByText(/high priority/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

it('clears completed tasks on click and disables the button while busy', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  const { rerender } = render(
    <TodoSummary stats={stats} busy={false} onClearCompleted={onClearCompleted} />,
  )
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  expect(onClearCompleted).toHaveBeenCalledTimes(1)
  rerender(
    <TodoSummary stats={stats} busy onClearCompleted={onClearCompleted} />,
  )
  expect(screen.getByRole('button', { name: 'Clear completed (1)' })).toBeDisabled()
})
