import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { todoFixture } from '../../../test/todoFixture'
import { Card } from '../../../design-system'
import { TodoItem } from './TodoItem'
import type { Todo } from '../types'

vi.mock('../../../design-system', () => import('../../../design-system/mocks'))

const handlers = () => ({
  busy: false,
  onEdit: vi.fn(),
  onToggle: vi.fn(),
  onDelete: vi.fn(),
})

function lastCardTone() {
  return vi.mocked(Card).mock.lastCall?.[0]?.tone
}

describe('TodoItem', () => {
  it('shows an active task and forwards edit requests', async () => {
    const user = userEvent.setup()
    const { busy, onEdit, onToggle, onDelete } = handlers()
    render(
      <TodoItem
        todo={todoFixture}
        busy={busy}
        onEdit={onEdit}
        onToggle={onToggle}
        onDelete={onDelete}
      />,
    )
    expect(
      screen.getByRole('heading', { name: todoFixture.title }),
    ).toBeVisible()
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

  it.each([
    ['low', 'neutral'],
    ['medium', 'info'],
    ['high', 'warning'],
  ] as const)(
    'tones the card for %s priority as %s',
    (priority: Todo['priority'], tone) => {
      const { busy, onEdit, onToggle, onDelete } = handlers()
      render(
        <TodoItem
          todo={{ ...todoFixture, priority }}
          busy={busy}
          onEdit={onEdit}
          onToggle={onToggle}
          onDelete={onDelete}
        />,
      )
      expect(lastCardTone()).toBe(tone)
    },
  )
})
