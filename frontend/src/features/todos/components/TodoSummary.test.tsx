import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { todoStatsFixture } from '../../../test/todoStatsFixture'
import { TodoSummary } from './TodoSummary'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('renders nothing until the stats have loaded', () => {
  const { container } = render(
    <TodoSummary stats={undefined} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

it('shows progress, deadlines and open high priority tasks', () => {
  render(
    <TodoSummary
      stats={{
        ...todoStatsFixture,
        overdue: 1,
        due_today: 2,
        active_by_priority: { low: 0, medium: 1, high: 2 },
      }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  const summary = screen.getByRole('region', { name: 'Task summary' })
  expect(summary).toHaveTextContent('1 of 4 done (25%)')
  expect(screen.getByText('1 overdue · 2 due today')).toBeInTheDocument()
  expect(screen.getByText('2 high priority open')).toBeInTheDocument()
})

it('hides deadlines, high priority count and the clear button when there are none', () => {
  render(
    <TodoSummary
      stats={{ ...todoStatsFixture, completed: 0, active: 4, completion_rate: 0 }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByText(/overdue|due today/)).not.toBeInTheDocument()
  expect(screen.queryByText(/high priority open/)).not.toBeInTheDocument()
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})

it('clears completed tasks when the button is clicked', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  render(
    <TodoSummary
      stats={todoStatsFixture}
      busy={false}
      onClearCompleted={onClearCompleted}
    />,
  )
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  expect(onClearCompleted).toHaveBeenCalledTimes(1)
})

it('disables clearing while another change is in progress', async () => {
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
