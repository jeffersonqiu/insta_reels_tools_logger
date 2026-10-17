import React from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'

import client from '../api/client'
import Library from './Library'
import ItemDetail from './ItemDetail'

vi.mock('../api/client', () => ({ default: { get: vi.fn() } }))

const item = {
  id: 'item-1', title: 'Agent canvas', summary: 'Build a visual workflow.',
  created_at: '2026-10-17T12:00:00Z', tags: ['agents'], key_ideas: ['Run roles in parallel'],
  concepts: ['Orchestration'], action_items: ['Try a planner'],
  source_url: 'https://www.instagram.com/reel/Example/',
  repositories: [{ name: 'OpenFlow', url: 'https://github.com/example/openflow', description: 'A canvas' }],
  raw_extraction: { tools: [{ name: 'OpenFlow', functionality: 'Connect roles.', problem_solved: 'Less glue code.' }] },
}

function renderLibrary(path = '/library') {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/library" element={<Library />} /><Route path="/items/:id" element={<ItemDetail />} /></Routes></MemoryRouter>)
}

function renderDetail(response = { item, video: { id: 'video-1', transcript: 'Source words', caption: 'Creator caption' } }) {
  client.get.mockResolvedValue({ data: response })
  return render(<MemoryRouter initialEntries={['/items/item-1?q=canvas&tag=agents']}><Routes><Route path="/items/:id" element={<ItemDetail />} /></Routes></MemoryRouter>)
}

beforeEach(() => vi.resetAllMocks())
afterEach(cleanup)

describe('Knowledge library', () => {
  it('loads older pages and searches their ideas and tags', async () => {
    const first = Array.from({ length: 200 }, (_, i) => ({ ...item, id: `first-${i}`, title: `Recent ${i}`, tags: ['recent'], concepts: [] }))
    client.get.mockResolvedValueOnce({ data: first }).mockResolvedValueOnce({ data: [{ ...item, id: 'older', title: 'Older insight', concepts: ['Rare technique'] }] })
    renderLibrary('/library?q=rare%20technique')
    expect(await screen.findByRole('link', { name: 'Older insight' })).toBeInTheDocument()
    expect(screen.queryByRole('link', { name: 'Recent 0' })).not.toBeInTheDocument()
    expect(client.get.mock.calls.map(([, options]) => options.params.offset)).toEqual([0, 200])
    fireEvent.change(screen.getByLabelText('Search your library'), { target: { value: '' } })
    fireEvent.click(screen.getByRole('button', { name: 'agents', exact: true }))
    expect(screen.getByRole('link', { name: 'Older insight' })).toHaveAttribute('href', '/items/older?tag=agents')
    expect(screen.queryByRole('link', { name: 'Recent 0' })).not.toBeInTheDocument()
  })

  it('preserves filters when opening an item and returning', async () => {
    client.get.mockResolvedValueOnce({ data: [item] }).mockResolvedValueOnce({ data: { item, video: null } }).mockResolvedValueOnce({ data: [item] })
    renderLibrary('/library?q=canvas&tag=agents')
    fireEvent.click(await screen.findByRole('link', { name: 'Agent canvas' }))
    await screen.findByRole('heading', { name: 'Agent canvas' })
    const back = screen.getByRole('link', { name: /Back to library/ })
    expect(back).toHaveAttribute('href', '/library?q=canvas&tag=agents')
    fireEvent.click(back)
    expect(await screen.findByLabelText('Search your library')).toHaveValue('canvas')
  })

  it('shows an empty state and lets users clear unmatched filters', async () => {
    client.get.mockResolvedValue({ data: [item] })
    renderLibrary('/library?q=nothing')
    expect(await screen.findByRole('heading', { name: 'No matching items' })).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }))
    expect(screen.getByRole('link', { name: 'Agent canvas' })).toBeInTheDocument()
  })

  it('shows new-library guidance when no knowledge items exist', async () => {
    client.get.mockResolvedValue({ data: [] })
    renderLibrary()
    expect(await screen.findByRole('heading', { name: 'Your library starts here' })).toBeInTheDocument()
    expect(screen.getByText(/Older saved Reels remain available in Tools/)).toBeInTheDocument()
  })

  it('retries a failed page without presenting partial results as a complete library', async () => {
    client.get.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: [item] })
    renderLibrary()
    expect(await screen.findByRole('alert')).toHaveTextContent('Could not load your library')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    expect(await screen.findByRole('link', { name: 'Agent canvas' })).toBeInTheDocument()
  })
})

describe('Knowledge item detail', () => {
  it('shows extracted knowledge, links, tools, and expandable source text', async () => {
    renderDetail()
    expect(await screen.findByRole('heading', { name: 'Agent canvas' })).toBeInTheDocument()
    for (const name of ['Summary', 'Key ideas', 'Action items', 'Concepts', 'Tools mentioned', 'Repositories & links', 'Source']) {
      expect(screen.getByRole('heading', { name })).toBeInTheDocument()
    }
    expect(screen.getByRole('link', { name: /OpenFlow/ })).toHaveAttribute('href', 'https://github.com/example/openflow')
    expect(screen.getByRole('link', { name: /Video details/ })).toHaveAttribute('href', '/videos/video-1')
    expect(screen.getByText('Transcript').closest('details')).not.toHaveAttribute('open')
    fireEvent.click(screen.getByText('Transcript'))
    expect(screen.getByText('Transcript').closest('details')).toHaveAttribute('open')
  })

  it('does not make unsafe or missing extracted URLs clickable', async () => {
    renderDetail({ item: { ...item, source_url: 'javascript:alert(1)', repositories: [{ name: 'Unsafe', url: 'javascript:alert(1)' }, { name: 'Missing', url: null }] }, video: null })
    await screen.findByRole('heading', { name: 'Agent canvas' })
    expect(screen.queryByRole('link', { name: /Unsafe|Missing|Watch Reel/ })).not.toBeInTheDocument()
    expect(screen.getAllByText('No web link provided in the source.')).toHaveLength(2)
    expect(screen.getByText('Source details are unavailable.')).toBeInTheDocument()
  })

  it('handles an unknown item and can recover on retry', async () => {
    client.get.mockRejectedValueOnce({ response: { status: 404 } }).mockResolvedValueOnce({ data: { item, video: null } })
    render(<MemoryRouter initialEntries={['/items/unknown']}><Routes><Route path="/items/:id" element={<ItemDetail />} /></Routes></MemoryRouter>)
    expect(await screen.findByRole('alert')).toHaveTextContent('This item could not be found.')
    fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Agent canvas' })).toBeInTheDocument())
  })
})
