import React from 'react'
import { Link, Route, Routes } from 'react-router-dom'
import Feed from './pages/Feed'
import VideoDetail from './pages/VideoDetail'

function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 bg-gray-950/80 px-4 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <Link to="/" className="text-lg font-semibold text-violet-400">
            AI Tools Tracker
          </Link>
        </div>
      </header>
      <main className="mx-auto w-full max-w-6xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Feed />} />
          <Route path="/videos/:id" element={<VideoDetail />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
