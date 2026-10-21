import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { TodoItem } from './TodoItem'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

beforeEach(() => {
  vi.clearAllMocks()
  vi.useFakeTimers({ toFake: ['Date'] })
  vi.setSystemTime(new Date(2026, 9, 15, 12))
})

afterEach(() => {
  vi.useRealTimers()
})

it('shows an active task and forwards edit requests', async () => {
  const user = userEvent.setup()
  const onEdit = vi.fn()
  const onToggle = vi.fn()
  const onDelete = vi.fn()
  render(
    <TodoItem
      todo={todoFixture}
      busy={false}
      onEdit={onEdit}
      onToggle={onToggle}
      onDelete={onDelete}
    />,
  )
  expect(screen.getByRole('heading', { name: todoFixture.title })).toBeVisible()
  expect(screen.getByText('To do')).toBeVisible()
  expect(screen.getByText('Medium')).toBeVisible()
  expect(screen.getByRole('checkbox')).not.toBeChecked()
  await user.click(
    screen.getByRole('button', { name: `Edit: ${todoFixture.title}` }),
  )
  expect(onEdit).toHaveBeenCalledTimes(1)
  expect(onToggle).not.toHaveBeenCalled()
  expect(onDelete).not.toHaveBeenCalled()
})

it('shows a completed task as checked and toggles it back to active', async () => {
  const user = userEvent.setup()
  const onToggle = vi.fn()
  render(
    <TodoItem
      todo={{ ...todoFixture, completed: true }}
      busy={false}
      onEdit={vi.fn()}
      onToggle={onToggle}
      onDelete={vi.fn()}
    />,
  )
  expect(screen.getByText('Completed')).toBeVisible()
  const checkbox = screen.getByRole('checkbox', {
    name: `Mark as active: ${todoFixture.title}`,
  })
  expect(checkbox).toBeChecked()
  await user.click(checkbox)
  expect(onToggle).toHaveBeenCalledTimes(1)
})

it('forwards delete requests from the delete button', async () => {
  const user = userEvent.setup()
  const onDelete = vi.fn()
  const onEdit = vi.fn()
  render(
    <TodoItem
      todo={todoFixture}
      busy={false}
      onEdit={onEdit}
      onToggle={vi.fn()}
      onDelete={onDelete}
    />,
  )
  await user.click(
    screen.getByRole('button', { name: `Delete: ${todoFixture.title}` }),
  )
  expect(onDelete).toHaveBeenCalledTimes(1)
  expect(onEdit).not.toHaveBeenCalled()
})

it('disables the checkbox and action buttons while busy', () => {
  render(
    <TodoItem
      todo={todoFixture}
      busy
      onEdit={vi.fn()}
      onToggle={vi.fn()}
      onDelete={vi.fn()}
    />,
  )
  expect(screen.getByRole('checkbox')).toBeDisabled()
  expect(
    screen.getByRole('button', { name: `Edit: ${todoFixture.title}` }),
  ).toBeDisabled()
  expect(
    screen.getByRole('button', { name: `Delete: ${todoFixture.title}` }),
  ).toBeDisabled()
})

it('shows an open task past its due date as overdue', () => {
  render(
    <TodoItem
      todo={{ ...todoFixture, due_date: '2026-10-05' }}
      busy={false}
      onEdit={vi.fn()}
      onToggle={vi.fn()}
      onDelete={vi.fn()}
    />,
  )
  expect(screen.getByText('5 Oct 2026 · overdue')).toBeVisible()
})

it('does not mark a completed task as overdue', () => {
  render(
    <TodoItem
      todo={{ ...todoFixture, completed: true, due_date: '2026-10-05' }}
      busy={false}
      onEdit={vi.fn()}
      onToggle={vi.fn()}
      onDelete={vi.fn()}
    />,
  )
  expect(screen.getByText('5 Oct 2026')).toBeVisible()
  expect(screen.queryByText(/overdue/)).not.toBeInTheDocument()
})

it('shows a due date without the overdue marker when it is still ahead', () => {
  render(
    <TodoItem
      todo={{ ...todoFixture, due_date: '2026-12-01' }}
      busy={false}
      onEdit={vi.fn()}
      onToggle={vi.fn()}
      onDelete={vi.fn()}
    />,
  )
  expect(screen.getByText('1 Dec 2026')).toBeVisible()
  expect(screen.queryByText(/overdue/)).not.toBeInTheDocument()
})
