import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import type { EvidenceListItem } from '../../types'
import EvidenceTable from '../EvidenceTable'

const ITEMS: EvidenceListItem[] = [
  {
    id: '1',
    evidence_number: 'EVD-001',
    case_id: 'c1',
    case_number: 'CASE-1',
    case_title: 'Case One',
    original_filename: 'clip.mp4',
    file_size: 2048,
    mime_type: 'video/mp4',
    sha256: null,
    status: 'uploaded',
    uploaded_at: '2026-08-10T10:00:00Z',
  },
  {
    id: '2',
    evidence_number: 'EVD-002',
    case_id: 'c2',
    case_number: null,
    case_title: null,
    original_filename: 'other.mov',
    file_size: 1048576,
    mime_type: 'video/quicktime',
    sha256: null,
    status: 'analyzed',
    uploaded_at: '2026-08-11T10:00:00Z',
  },
]

describe('EvidenceTable', () => {
  it('renders a row per evidence item', () => {
    render(<EvidenceTable items={ITEMS} />)
    expect(screen.getAllByTestId('evidence-row')).toHaveLength(2)
    expect(screen.getByText('EVD-001')).toBeInTheDocument()
    expect(screen.getByText('other.mov')).toBeInTheDocument()
  })

  it('formats file sizes', () => {
    render(<EvidenceTable items={ITEMS} />)
    expect(screen.getByText('2.0 KB')).toBeInTheDocument()
    expect(screen.getByText('1.0 MB')).toBeInTheDocument()
  })

  it('renders a status badge per row', () => {
    render(<EvidenceTable items={ITEMS} />)
    expect(screen.getAllByTestId('status-badge')).toHaveLength(2)
  })

  it('calls onRowClick when a row is clicked', async () => {
    const user = userEvent.setup()
    const onRowClick = vi.fn()
    render(<EvidenceTable items={ITEMS} onRowClick={onRowClick} />)
    await user.click(screen.getByText('clip.mp4'))
    expect(onRowClick).toHaveBeenCalledWith(ITEMS[0])
  })

  it('shows the empty message when there are no items', () => {
    render(<EvidenceTable items={[]} />)
    expect(screen.getByText('No evidence yet.')).toBeInTheDocument()
  })
})
