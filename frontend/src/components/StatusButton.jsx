import React from 'react'

function StatusButton({ children, onClick, variant = 'default' }) {
  const variants = {
    default: 'border-gray-700 bg-gray-900 text-gray-200 hover:bg-gray-800',
    success: 'border-emerald-600/50 bg-emerald-600/20 text-emerald-300 hover:bg-emerald-600/30',
    danger: 'border-rose-600/50 bg-rose-600/20 text-rose-300 hover:bg-rose-600/30',
    accent: 'border-violet-600/50 bg-violet-600/20 text-violet-300 hover:bg-violet-600/30',
  }
  return (
    <button onClick={onClick} className={`rounded-md border px-2.5 py-1.5 text-xs ${variants[variant]}`}>
      {children}
    </button>
  )
}

export default StatusButton
