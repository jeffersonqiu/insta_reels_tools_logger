import React from 'react'
import { Link, NavLink, Route, Routes } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import Feed from './pages/Feed'
import VideoDetail from './pages/VideoDetail'

function LogoMark({ className = 'h-9 w-9' }) {
  return (
    <svg className={className} viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden>
      <rect width="512" height="512" rx="112" fill="#2a2724" />
      <rect x="88" y="118" width="336" height="72" rx="20" fill="#d4a574" />
      <rect x="88" y="220" width="256" height="72" rx="20" fill="#c49a6c" opacity=".95" />
      <rect x="88" y="322" width="304" height="72" rx="20" fill="#a89078" opacity=".9" />
      <circle cx="392" cy="152" r="28" fill="#e8c4a0" opacity=".9" />
    </svg>
  )
}

const navLinkClass = ({ isActive }) =>
  `rounded-lg px-3 py-2.5 text-sm font-medium transition outline-none focus-visible:ring-2 focus-visible:ring-accent min-h-[44px] inline-flex items-center touch-manipulation ${
    isActive
      ? 'bg-white/[0.08] text-ink ring-1 ring-inset ring-accent/35'
      : 'text-ink-muted hover:bg-white/[0.05] hover:text-ink'
  }`

function App() {
  return (
    <div className="min-h-screen text-ink">
      <header className="sticky top-0 z-20 border-b border-stroke bg-canvas-deep/90 backdrop-blur-xl">
        <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:gap-4 md:py-3.5">
          <Link
            to="/"
            className="group flex w-fit items-center gap-3 rounded-xl outline-none ring-0 transition focus-visible:ring-2 focus-visible:ring-accent"
          >
            <span className="relative shrink-0 transition duration-300 group-hover:scale-[1.02]">
              <LogoMark />
            </span>
            <span className="flex flex-col leading-tight">
              <span className="font-brand text-lg font-semibold leading-snug tracking-tight text-ink">
                AI Tools Tracker
              </span>
              <span className="font-mono text-[11px] font-medium uppercase tracking-[0.18em] text-ink-faint">
                From reels → your stack
              </span>
            </span>
          </Link>
          <nav className="flex flex-wrap gap-1 border-t border-stroke/60 pt-3 sm:border-t-0 sm:pt-0" aria-label="Main">
            <NavLink to="/dashboard" className={navLinkClass} end={false}>
              Overview
            </NavLink>
            <NavLink to="/" className={navLinkClass} end>
              Tools
            </NavLink>
          </nav>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-8 md:py-10">
        <Routes>
          <Route path="/" element={<Feed />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/videos/:id" element={<VideoDetail />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
