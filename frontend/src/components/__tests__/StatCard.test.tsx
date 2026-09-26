import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import StatCard from '../StatCard'

describe('StatCard', () => {
  it('renders the label and value', () => {
    render(<StatCard label="Total Evidence" value={42} />)
    expect(screen.getByText('Total Evidence')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders a string value and hint', () => {
    render(<StatCard label="Status" value="Active" hint="as of today" />)
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('as of today')).toBeInTheDocument()
  })
})
