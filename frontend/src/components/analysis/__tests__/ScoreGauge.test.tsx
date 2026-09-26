import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { AnomalyScore } from '../../../types'
import ScoreGauge from '../ScoreGauge'

const SCORE: AnomalyScore = {
  evidence_id: 'ev-1',
  analysis_id: 'a-1',
  score: 15,
  category: 'low',
  factors: [
    {
      name: 'metadata_inconsistency',
      label: 'Metadata inconsistency',
      max_points: 15,
      points: 15,
      reason: 'Declared frame count does not match duration × frame rate',
    },
    {
      name: 'duration_difference',
      label: 'Duration difference',
      max_points: 20,
      points: 0,
      reason: 'Duration matches the reference',
    },
    {
      name: 'frame_discontinuity',
      label: 'Frame discontinuity',
      max_points: 25,
      points: 0,
      reason: 'No abrupt frame discontinuities detected',
    },
    {
      name: 'encoding_difference',
      label: 'Encoding difference',
      max_points: 15,
      points: 0,
      reason: 'Encoding matches the reference',
    },
    {
      name: 'unnatural_frame_diff_cluster',
      label: 'Unnatural frame-diff cluster',
      max_points: 15,
      points: 0,
      reason: 'No clustered frame-difference events detected',
    },
    {
      name: 'single_scene_changes',
      label: 'Single scene changes',
      max_points: 5,
      points: 0,
      reason: 'No frame-difference events recorded',
    },
  ],
  computed_at: '2026-08-11T12:00:00Z',
}

describe('ScoreGauge', () => {
  it('shows the score, category and factor breakdown', () => {
    render(<ScoreGauge score={SCORE} />)
    expect(screen.getByTestId('score-gauge')).toHaveAccessibleName(
      'Anomaly Indicator Score 15 out of 100, Low',
    )
    expect(screen.getByTestId('score-value')).toHaveTextContent('15')
    expect(screen.getByTestId('score-category')).toHaveTextContent('Low')
    expect(screen.getByTestId('score-factors')).toHaveTextContent(
      'Declared frame count does not match duration × frame rate',
    )
  })

  it('shows all factor weights and reasons, not a black-box number', () => {
    render(<ScoreGauge score={SCORE} />)
    const factors = screen.getByTestId('score-factors')
    expect(factors).toHaveTextContent('15/15')
    expect(factors).toHaveTextContent('0/20')
    expect(factors).toHaveTextContent('No abrupt frame discontinuities detected')
  })

  it('labels the score as indicators, not a tampering verdict', () => {
    render(<ScoreGauge score={SCORE} />)
    expect(
      screen.getByText(/not a probability of tampering/i),
    ).toBeInTheDocument()
  })

  it('shows a hint when no analysis has run', () => {
    render(
      <ScoreGauge
        score={{
          evidence_id: 'ev-1',
          analysis_id: null,
          score: null,
          category: null,
          factors: [],
          computed_at: null,
        }}
      />,
    )
    expect(screen.getByText(/no scene-change analysis yet/i)).toBeInTheDocument()
  })
})
