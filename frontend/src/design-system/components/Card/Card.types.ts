import type { HTMLAttributes } from 'react'

export type CardVariant = 'outline' | 'elevated'

export type CardTone = 'default' | 'neutral' | 'info' | 'warning'

/** Props for the Card component. */
export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Visual style of the card. */
  variant?: CardVariant
  /** Background tint of the card; `default` keeps the plain surface. */
  tone?: CardTone
}
