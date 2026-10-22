import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { expect, it, vi } from 'vitest'
import { Card } from '../../../design-system'
import { todoFixture } from '../../../test/todoFixture'
import { TodoItem } from './TodoItem'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

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

it('tones the card by priority: high warns, medium is info, low is neutral', () => {
  const cases = [
    ['low', 'neutral'],
    ['medium', 'info'],
    ['high', 'warning'],
  ] as const
  for (const [priority, tone] of cases) {
    const { unmount } = render(
      <TodoItem
        todo={{ ...todoFixture, priority }}
        busy={false}
        onEdit={vi.fn()}
        onToggle={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(vi.mocked(Card).mock.lastCall?.[0]).toEqual(
      expect.objectContaining({ tone }),
    )
    unmount()
  }
})
