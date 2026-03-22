import React from 'react'

function StatusButton({ children, onClick, variant = 'default' }) {
  const variants = {
    default:
      'border-stroke bg-white/[0.04] text-ink-muted hover:border-stroke hover:bg-white/[0.07] hover:text-ink',
    success:
      'border-mint-dim bg-mint-dim text-mint hover:border-mint/40 hover:bg-mint-dim hover:brightness-110',
    danger:
      'border-coral-dim bg-coral-dim text-coral hover:border-coral/40 hover:bg-coral-dim hover:brightness-110',
    accent:
      'border-accent-dim bg-accent-dim text-accent hover:border-accent/35 hover:bg-accent-dim hover:brightness-110',
  }
  return (
    <button
      type="button"
      onClick={onClick}
      className={`min-h-[44px] touch-manipulation rounded-lg border px-3 py-2.5 text-xs font-medium transition duration-200 outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-canvas-deep focus-visible:ring-accent active:scale-[0.97] sm:min-h-0 sm:py-2 ${variants[variant]}`}
    >
      {children}
    </button>
  )
}

export default StatusButton
