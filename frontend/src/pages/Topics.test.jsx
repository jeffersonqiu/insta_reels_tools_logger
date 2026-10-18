import React from 'react'
import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { cleanup, fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import client from '../api/client'
import Topics from './Topics'

vi.mock('../api/client', () => ({ default: { get: vi.fn() } }))
beforeEach(() => vi.resetAllMocks())
afterEach(cleanup)

const topic = { id: 'agents', name: 'Agents & orchestration', description: 'Coordinate work.', guide: 'Try a small workflow.', count: 1, catch_all: false }
const source = { id: 'item-1', title: 'Agent canvas', created_at: '2026-03-01T00:00:00Z', summary: 'A saved workflow.', review_reasons: ['Source is incomplete.'] }
function show(path = '/topics') {
  return render(<MemoryRouter initialEntries={[path]}><Routes><Route path="/topics" element={<Topics />} /><Route path="/topics/:topicId" element={<Topics />} /></Routes></MemoryRouter>)
}

it('shows topic shelves and catch-all queues even when empty', async () => {
  client.get.mockResolvedValue({ data: [topic, { id: 'inbox', name: 'Inbox', description: 'Unclassified', count: 0, catch_all: true }, { id: 'needs-review', name: 'Needs review', description: 'Uncertain sources', count: 1, catch_all: true }] })
  show()
  expect(await screen.findByRole('link', { name: topic.name })).toHaveAttribute('href', '/topics/agents')
  expect(screen.getByRole('link', { name: 'Inbox · 0' })).toHaveAttribute('href', '/topics/inbox')
  expect(screen.getByRole('link', { name: 'Needs review · 1' })).toBeInTheDocument()
})

it('connects ideas and actions to their original sources and shows review reasons', async () => {
  client.get.mockResolvedValue({ data: { ...topic, items: [source], ideas: [{ text: 'Split agent roles', sources: [source] }], actions: [{ text: 'Try a planner', sources: [source] }] } })
  show('/topics/agents')
  expect(await screen.findByRole('heading', { name: topic.name })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: 'Ideas to connect' })).toBeInTheDocument()
  expect(screen.getByText('Try a planner')).toBeInTheDocument()
  expect(screen.getByText('Source is incomplete.')).toBeInTheDocument()
  expect(screen.getAllByRole('link', { name: /Agent canvas/ }).every((link) => link.getAttribute('href') === '/items/item-1')).toBe(true)
})

it('keeps an empty queue visible and handles unknown topics', async () => {
  client.get.mockResolvedValue({ data: { ...topic, items: [], ideas: [], actions: [] } })
  show('/topics/agents')
  expect(await screen.findByText(/This shelf is clear for now/)).toBeInTheDocument()
})

it('can retry failed topic loading without stale results', async () => {
  client.get.mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce({ data: [topic] })
  show()
  expect(await screen.findByRole('alert')).toHaveTextContent('Could not load your topics')
  fireEvent.click(screen.getByRole('button', { name: 'Try again' }))
  expect(await screen.findByRole('link', { name: topic.name })).toBeInTheDocument()
})

it('navigates list to detail and back without rendering the previous response shape', async () => {
  client.get.mockResolvedValueOnce({ data: [topic] }).mockResolvedValueOnce({ data: { ...topic, items: [source], ideas: [], actions: [] } }).mockResolvedValueOnce({ data: [topic] })
  show()
  fireEvent.click(await screen.findByRole('link', { name: topic.name }))
  expect(await screen.findByRole('heading', { name: 'Sources · 1' })).toBeInTheDocument()
  fireEvent.click(screen.getByRole('link', { name: /All topics/ }))
  expect(await screen.findByRole('heading', { name: 'Browse by topic' })).toBeInTheDocument()
})
