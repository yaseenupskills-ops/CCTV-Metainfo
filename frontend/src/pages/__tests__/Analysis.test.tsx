import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { Analysis as AnalysisModel } from '../../types'
import Analysis from '../Analysis'

// Only the network layer is mocked; the real hooks and QueryClient run, so the
// component is exercised as it ships.
const listEvidence = vi.fn()
const listEvidenceAnalyses = vi.fn()

vi.mock('../../api/client', () => ({
  listEvidence: (...args: unknown[]) => listEvidence(...args),
  listEvidenceAnalyses: (...args: unknown[]) => listEvidenceAnalyses(...args),
  extractMetadata: vi.fn(),
  runAnalysis: vi.fn(),
}))

vi.mock('react-router-dom', () => ({
  Link: ({ children }: { children: React.ReactNode }) => <a href="/detail">{children}</a>,
  useParams: () => ({}),
}))

function makeAnalysis(overrides: Partial<AnalysisModel> = {}): AnalysisModel {
  return {
    id: 'a1',
    evidence_id: 'e1',
    analysis_type: 'frame_sampling',
    status: 'completed',
    params: { sampling_rate: 1 },
    started_at: '2026-03-01T12:00:00Z',
    completed_at: '2026-03-01T12:00:05Z',
    error_message: null,
    ...overrides,
  }
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  })
  return render(
    <QueryClientProvider client={queryClient}>
      <Analysis />
    </QueryClientProvider>,
  )
}

/** The text of the table's Result column for each rendered row. */
function resultColumn(): string[] {
  return screen
    .getAllByRole('row')
    .slice(1) // drop the header row
    .map((row) => row.querySelectorAll('td')[5]?.textContent?.trim() ?? '')
}

describe('Analysis result column', () => {
  beforeEach(() => {
    listEvidence.mockReset()
    listEvidenceAnalyses.mockReset()
    listEvidence.mockResolvedValue({
      items: [
        {
          id: 'e1',
          evidence_number: 'EV-1',
          original_filename: 'clip.mp4',
          status: 'analyzed',
        },
      ],
    })
  })

  // The regression this guards: list rows only carry `summary`, so a renderer
  // reading `result` showed a dash in this column for every completed run.

  it('renders the event count from summary on a list row', async () => {
    listEvidenceAnalyses.mockResolvedValue([
      makeAnalysis({ analysis_type: 'scene_change', summary: { events: 3 } }),
    ])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['3 events']))
  })

  it('uses the singular form for exactly one event', async () => {
    listEvidenceAnalyses.mockResolvedValue([
      makeAnalysis({ analysis_type: 'scene_change', summary: { events: 1 } }),
    ])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['1 event']))
  })

  it('renders zero events rather than a dash for a completed empty run', async () => {
    listEvidenceAnalyses.mockResolvedValue([
      makeAnalysis({ analysis_type: 'scene_change', summary: { events: 0 } }),
    ])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['0 events']))
  })

  it('renders the frame count from summary on a list row', async () => {
    listEvidenceAnalyses.mockResolvedValue([makeAnalysis({ summary: { frames_sampled: 240 } })])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['240 frames sampled']))
  })

  it('still falls back to the full result when only that is present', async () => {
    // The detail response carries `result` with the raw events array.
    listEvidenceAnalyses.mockResolvedValue([
      makeAnalysis({
        analysis_type: 'scene_change',
        result: { events: [{ timestamp: 1 }, { timestamp: 2 }] },
      }),
    ])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['2 events']))
  })

  it('renders a dash for an analysis with no result yet', async () => {
    listEvidenceAnalyses.mockResolvedValue([makeAnalysis({ status: 'queued', summary: null })])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['—']))
  })

  it('shows the error message instead of a result for a failed analysis', async () => {
    listEvidenceAnalyses.mockResolvedValue([
      makeAnalysis({ status: 'failed', summary: null, error_message: 'ffprobe crashed' }),
    ])

    renderPage()

    await waitFor(() => expect(resultColumn()).toEqual(['ffprobe crashed']))
  })

  it('renders every row of a mixed history', async () => {
    listEvidenceAnalyses.mockResolvedValue([
      makeAnalysis({ id: 'a1', analysis_type: 'scene_change', summary: { events: 2 } }),
      makeAnalysis({ id: 'a2', summary: { frames_sampled: 60 } }),
      makeAnalysis({ id: 'a3', status: 'processing', summary: null }),
    ])

    renderPage()

    await waitFor(() =>
      expect(resultColumn()).toEqual(['2 events', '60 frames sampled', '—']),
    )
  })
})
