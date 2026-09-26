import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'

import type { EvidenceTimeline } from '../../../types'
import Timeline from '../Timeline'

const TIMELINE: EvidenceTimeline = {
  evidence_id: 'ev-1',
  duration: 10,
  analysis_id: 'a-1',
  analysis_status: 'completed',
  segments: [
    { kind: 'normal', start: 0, end: 4, severity: null, event_index: null },
    { kind: 'anomaly', start: 4, end: 4, severity: 'high', event_index: 0 },
    { kind: 'normal', start: 4, end: 10, severity: null, event_index: null },
  ],
  events: [
    {
      timestamp: 4,
      severity: 'high',
      detection_method: 'frame_difference',
      diff_score: 0.8421,
      prev_frame: 40,
      current_frame: 41,
      metrics: {
        mad: 0.9,
        histogram_diff: 0.5,
        ssim: 0.2,
        phash_distance: 0.7,
      },
      analysis_id: 'a-1',
      analysis_type: 'scene_change',
    },
  ],
}

describe('Timeline', () => {
  it('renders the track, normal segments and anomaly markers', () => {
    render(
      <Timeline
        segments={TIMELINE.segments}
        events={TIMELINE.events}
        duration={TIMELINE.duration}
      />,
    )
    expect(screen.getByTestId('timeline-track')).toBeInTheDocument()
    expect(screen.getAllByTestId('timeline-segment')).toHaveLength(2)
    expect(screen.getAllByTestId('timeline-anomaly')).toHaveLength(1)
    expect(screen.getByLabelText(/Potential anomaly at/)).toBeInTheDocument()
    expect(screen.getByText('Normal')).toBeInTheDocument()
    expect(screen.getByText('Potential anomaly')).toBeInTheDocument()
  })

  it('opens the detail drawer when an anomaly is clicked', async () => {
    const user = userEvent.setup()
    render(
      <Timeline
        segments={TIMELINE.segments}
        events={TIMELINE.events}
        duration={TIMELINE.duration}
      />,
    )

    expect(screen.queryByTestId('timeline-drawer')).not.toBeInTheDocument()
    await user.click(screen.getByTestId('timeline-anomaly'))

    const drawer = screen.getByTestId('timeline-drawer')
    expect(drawer).toBeInTheDocument()
    expect(drawer).toHaveTextContent('frame_difference')
    expect(drawer).toHaveTextContent('0.8421')
    expect(drawer).toHaveTextContent('40')
    expect(drawer).toHaveTextContent('41')
    expect(drawer).toHaveTextContent('0.9')
    expect(drawer).toHaveTextContent('Potential anomaly')
  })

  it('shows an empty message when there are no segments', () => {
    render(<Timeline segments={[]} events={[]} duration={null} />)
    expect(screen.getByText(/Run a scene-change analysis/i)).toBeInTheDocument()
  })
})
