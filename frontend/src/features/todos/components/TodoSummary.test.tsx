import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { statsFixture } from '../../../test/statsFixture'
import { TodoSummary } from './TodoSummary'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('renders nothing until stats are loaded', () => {
  const { container } = render(
    <TodoSummary stats={undefined} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

it('shows progress, deadlines and open high priority count', () => {
  render(
    <TodoSummary
      stats={{
        ...statsFixture,
        overdue: 2,
        due_today: 1,
        active_by_priority: { low: 0, medium: 0, high: 3 },
      }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  const summary = screen.getByRole('region', { name: 'Task summary' })
  expect(summary).toHaveTextContent('1 of 4 done (25%)')
  expect(summary).toHaveTextContent('2 overdue · 1 due today')
  expect(summary).toHaveTextContent('3 high priority open')
})

it('hides deadline and high priority notes when there are none', () => {
  render(
    <TodoSummary stats={statsFixture} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(screen.queryByText(/overdue|due today/)).not.toBeInTheDocument()
  expect(screen.queryByText(/high priority open/)).not.toBeInTheDocument()
})

it('requests clearing completed tasks and disables the button while busy', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  const { rerender } = render(
    <TodoSummary
      stats={statsFixture}
      busy={false}
      onClearCompleted={onClearCompleted}
    />,
  )
  await user.click(
    screen.getByRole('button', { name: 'Clear completed (1)' }),
  )
  expect(onClearCompleted).toHaveBeenCalledTimes(1)
  rerender(
    <TodoSummary
      stats={statsFixture}
      busy
      onClearCompleted={onClearCompleted}
    />,
  )
  expect(
    screen.getByRole('button', { name: 'Clear completed (1)' }),
  ).toBeDisabled()
})

it('omits the clear button when no task is completed', () => {
  render(
    <TodoSummary
      stats={{ ...statsFixture, completed: 0, active: 4, completion_rate: 0 }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})
