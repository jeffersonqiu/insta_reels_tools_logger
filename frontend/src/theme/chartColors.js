/**
 * Solid hex colors for data viz. Tailwind opacity modifiers (e.g. bg-chart-1/90) on
 * CSS-variable colors often compile to invalid backgrounds in production, so bars
 * disappear. Use these for inline style backgroundColor.
 * Values mirror src/index.css :root tokens.
 */
export const CHART_FILL = {
  c1: '#5eead4',
  c2: '#fcd34d',
  c3: '#fb923c',
  accent: '#c4b5fd',
  mint: '#5eead4',
  coral: '#fb7185',
}

/** KPI card gradient + border + headline numeral color */
export const STAT_CARD_ACCENTS = {
  mint: {
    border: '1px solid rgba(94, 234, 212, 0.28)',
    backgroundImage: 'linear-gradient(to bottom right, rgba(94, 234, 212, 0.22), transparent)',
    valueColor: '#5eead4',
  },
  amber: {
    border: '1px solid rgba(252, 211, 77, 0.28)',
    backgroundImage: 'linear-gradient(to bottom right, rgba(252, 211, 77, 0.2), transparent)',
    valueColor: '#fcd34d',
  },
  orange: {
    border: '1px solid rgba(251, 146, 60, 0.28)',
    backgroundImage: 'linear-gradient(to bottom right, rgba(251, 146, 60, 0.2), transparent)',
    valueColor: '#fb923c',
  },
  violet: {
    border: '1px solid rgba(196, 181, 253, 0.28)',
    backgroundImage: 'linear-gradient(to bottom right, rgba(196, 181, 253, 0.2), transparent)',
    valueColor: '#c4b5fd',
  },
}
