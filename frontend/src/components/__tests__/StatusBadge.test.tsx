import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import StatusBadge from '../StatusBadge'

describe('StatusBadge', () => {
  it('renders a humanized status label', () => {
    render(<StatusBadge status="metadata_extracted" />)
    expect(screen.getByText('metadata extracted')).toBeInTheDocument()
  })

  it('applies a color class for known statuses', () => {
    render(<StatusBadge status="completed" />)
    const badge = screen.getByTestId('status-badge')
    expect(badge.className).toContain('text-ok')
  })

  it('falls back to a neutral style for unknown statuses', () => {
    render(<StatusBadge status="unknown_status" />)
    const badge = screen.getByTestId('status-badge')
    expect(badge.className).toContain('text-slate-300')
  })
})
