import { css } from 'styled-components'
import type { CardTone, CardVariant } from './Card.types'

/** Visual styles mapped by card variant. */
export const cardVariantStyles: Record<CardVariant, ReturnType<typeof css>> = {
  outline: css`
    border: 1px solid ${({ theme }) => theme.colors.border};
    background: ${({ theme }) => theme.colors.surface};
  `,
  elevated: css`
    border: 1px solid transparent;
    background: ${({ theme }) => theme.colors.surface};
    box-shadow: ${({ theme }) => theme.shadows.card};
  `,
}

/** Background tints mapped by card tone, applied over the variant. */
export const cardToneStyles: Record<CardTone, ReturnType<typeof css>> = {
  default: css``,
  neutral: css`
    background: ${({ theme }) => theme.colors.surfaceAlt};
  `,
  info: css`
    background: rgba(60, 90, 137, 0.08);
  `,
  warning: css`
    background: rgba(180, 71, 27, 0.08);
  `,
}
