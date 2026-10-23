import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { statsFixture } from '../../../test/statsFixture'
import { TodoSummary } from './TodoSummary'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

it('shows nothing until the stats have loaded', () => {
  const { container } = render(
    <TodoSummary stats={undefined} busy={false} onClearCompleted={vi.fn()} />,
  )
  expect(container).toBeEmptyDOMElement()
})

it('describes progress, deadlines and open high-priority tasks', () => {
  render(
    <TodoSummary
      stats={{ ...statsFixture, overdue: 1, due_today: 2, active_by_priority: { low: 0, medium: 0, high: 2 } }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.getByText('1 of 3 done (33%)')).toBeInTheDocument()
  expect(screen.getByText('1 overdue · 2 due today')).toBeInTheDocument()
  expect(screen.getByText('2 high priority open')).toBeInTheDocument()
})

it('omits the deadline badge and high-priority line when neither applies', () => {
  render(
    <TodoSummary
      stats={{ ...statsFixture, active_by_priority: { low: 0, medium: 2, high: 0 } }}
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
    <TodoSummary stats={statsFixture} busy={false} onClearCompleted={onClearCompleted} />,
  )
  await user.click(screen.getByRole('button', { name: 'Clear completed (1)' }))
  expect(onClearCompleted).toHaveBeenCalledTimes(1)
})

it('hides the clear action when no task is completed', () => {
  render(
    <TodoSummary
      stats={{ ...statsFixture, completed: 0, active: 3 }}
      busy={false}
      onClearCompleted={vi.fn()}
    />,
  )
  expect(screen.queryByRole('button', { name: /Clear completed/ })).not.toBeInTheDocument()
})

it('disables clearing completed tasks while other task work is in progress', async () => {
  const user = userEvent.setup()
  const onClearCompleted = vi.fn()
  render(
    <TodoSummary stats={statsFixture} busy onClearCompleted={onClearCompleted} />,
  )
  const button = screen.getByRole('button', { name: 'Clear completed (1)' })
  expect(button).toBeDisabled()
  await user.click(button)
  expect(onClearCompleted).not.toHaveBeenCalled()
})
