import React from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'

import FilterTabs from './FilterTabs'

describe('FilterTabs', () => {
  it('renders labels and counts and triggers tab change', () => {
    const onChange = vi.fn()
    render(
      <FilterTabs
        activeTab="to_explore"
        counts={{ to_explore: 1, implemented: 2, not_interested: 3, all: 6 }}
        onChange={onChange}
      />,
    )

    expect(screen.getByText(/To Explore/i)).toBeInTheDocument()
    fireEvent.click(screen.getByText(/Implemented/i))
    expect(onChange).toHaveBeenCalledWith('implemented')
  })
})
