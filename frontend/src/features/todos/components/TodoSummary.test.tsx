import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { TodoSummary } from './TodoSummary'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('renders nothing until the statistics have loaded', () => {
  const { container } = render(
    <TodoSummary stats={undefined} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

it('shows progress, deadline warnings and open high-priority tasks', () => {
  render(
    <TodoSummary stats={todoStatsFixture} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(screen.getByText('1 of 4 done (25%)')).toBeInTheDocument()
  expect(screen.getByText('1 overdue · 2 due today')).toBeInTheDocument()
  expect(screen.getByText('2 high priority open')).toBeInTheDocument()
})

it('hides the deadline warning and high-priority line when neither applies', () => {
  render(
    <TodoSummary
      stats={{
        ...todoStatsFixture,
        overdue: 0,
        due_today: 0,
        active_by_priority: { low: 0, medium: 3, high: 0 },
      }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByText(/overdue|due today/)).not.toBeInTheDocument()
  expect(screen.queryByText(/high priority open/)).not.toBeInTheDocument()
})

it('offers to clear the completed tasks and reports the count', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  render(
    <TodoSummary
      stats={{ ...todoStatsFixture, completed: 3 }}
      busy={false}
      onClearCompleted={onClearCompleted}
    />,
  )
  await user.click(screen.getByRole('button', { name: 'Clear completed (3)' }))
  expect(onClearCompleted).toHaveBeenCalledTimes(1)
})

it('does not offer to clear completed tasks when none are completed', () => {
  render(
    <TodoSummary
      stats={{ ...todoStatsFixture, completed: 0, active: 4, completion_rate: 0 }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

it('disables clearing completed tasks while another change is in progress', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  render(
    <TodoSummary stats={todoStatsFixture} busy onClearCompleted={onClearCompleted} />,
  )
  const button = screen.getByRole('button', { name: 'Clear completed (1)' })
  expect(button).toBeDisabled()
  await user.click(button)
  expect(onClearCompleted).not.toHaveBeenCalled()
})
