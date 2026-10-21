import { CheckCheck } from 'lucide-react'
import type { TodoStats } from '../types'
import { describeDeadlines, describeProgress } from '../utils/todos'
import { Badge, Button, Text } from '../../../design-system'

export function TodoSummary({
  stats,
  busy,
  onClearCompleted,
}: {
  stats: TodoStats | undefined
  busy: boolean
  onClearCompleted: () => void
}) {
  if (!stats) return null
  const deadlines = describeDeadlines(stats)
  return (
    <section className="row spread" aria-label="Task summary">
      <div className="row compact">
        <Text as="span">{describeProgress(stats)}</Text>
        {deadlines && <Badge variant="warning">{deadlines}</Badge>}
        {stats.active_by_priority.high > 0 && (
          <Text as="span" muted size="small">
            {stats.active_by_priority.high} high priority open
          </Text>
        )}
      </div>
      {stats.completed > 0 && (
        <Button
          variant="ghost"
          size="small"
          disabled={busy}
          onClick={onClearCompleted}
        >
          <CheckCheck size={16} aria-hidden="true" />
          Clear completed ({stats.completed})
        </Button>
      )}
    </section>
  )
}
