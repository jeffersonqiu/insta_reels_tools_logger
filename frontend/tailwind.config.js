/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx,ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'ui-monospace', 'monospace'],
        display: ['Outfit', 'system-ui', 'sans-serif'],
      },
      colors: {
        canvas: {
          DEFAULT: 'var(--color-canvas)',
          deep: 'var(--color-canvas-deep)',
        },
        elevated: 'var(--color-elevated)',
        stroke: 'var(--color-stroke)',
        ink: {
          DEFAULT: 'var(--color-ink)',
          muted: 'var(--color-ink-muted)',
          faint: 'var(--color-ink-faint)',
        },
        accent: {
          DEFAULT: 'var(--color-accent)',
          dim: 'var(--color-accent-dim)',
          glow: 'var(--color-accent-glow)',
        },
        mint: {
          DEFAULT: 'var(--color-mint)',
          dim: 'var(--color-mint-dim)',
        },
        coral: {
          DEFAULT: 'var(--color-coral)',
          dim: 'var(--color-coral-dim)',
        },
        chart: {
          1: 'var(--color-chart-1)',
          '1-dim': 'var(--color-chart-1-dim)',
          2: 'var(--color-chart-2)',
          '2-dim': 'var(--color-chart-2-dim)',
          3: 'var(--color-chart-3)',
          '3-dim': 'var(--color-chart-3-dim)',
        },
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        'card-hover': 'var(--shadow-card-hover)',
        glow: 'var(--shadow-glow)',
      },
      animation: {
        'fade-up': 'fadeUp 0.55s cubic-bezier(0.22, 1, 0.36, 1) forwards',
        shimmer: 'shimmer 1.2s ease-in-out infinite',
      },
      keyframes: {
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(14px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '200% 0' },
          '100%': { backgroundPosition: '-200% 0' },
        },
      },
      backgroundImage: {
        'noise-soft':
          "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.04'/%3E%3C/svg%3E\")",
      },
    },
  },
  plugins: [],
}
