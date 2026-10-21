import styled from 'styled-components'
import type { CardTone, CardVariant } from './Card.types'
import { cardToneStyles, cardVariantStyles } from './Card.variants'

interface BaseCardStyleProps {
  $variant: CardVariant
  $tone: CardTone
}

/** Styled primitive used by the public Card component. */
export const BaseCard = styled.div<BaseCardStyleProps>`
  padding: ${({ theme }) => theme.spacing.lg};
  border-radius: ${({ theme }) => theme.radii.lg};
  display: grid;
  gap: ${({ theme }) => theme.spacing.md};

  ${({ $variant }) => cardVariantStyles[$variant]}
  ${({ $tone }) => cardToneStyles[$tone]}
`
