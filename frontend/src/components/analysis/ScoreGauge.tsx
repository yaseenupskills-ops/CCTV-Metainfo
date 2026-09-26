import type { AnomalyScore } from '../../types'

const CATEGORY_COLORS: Record<string, string> = {
  low: '#22c55e',
  moderate: '#eab308',
  high: '#ef4444',
  very_high: '#a855f7',
}

const CATEGORY_LABELS: Record<string, string> = {
  low: 'Low',
  moderate: 'Moderate',
  high: 'High',
  very_high: 'Very high',
}

const CATEGORY_TEXT: Record<string, string> = {
  low: 'text-ok',
  moderate: 'text-warn',
  high: 'text-bad',
  very_high: 'text-info',
}

const RADIUS = 54
const CIRCUMFERENCE = 2 * Math.PI * RADIUS

interface ScoreGaugeProps {
  score: AnomalyScore
}

export default function ScoreGauge({ score }: ScoreGaugeProps) {
  if (score.score === null || score.category === null) {
    return (
      <div className="rounded-xl border border-edge bg-panel p-5 text-sm text-slate-500">
        No scene-change analysis yet. Run one to compute the anomaly indicator
        score.
      </div>
    )
  }

  const color = CATEGORY_COLORS[score.category] ?? '#94a3b8'
  const progress = Math.min(1, Math.max(0, score.score / 100))
  const dashOffset = CIRCUMFERENCE * (1 - progress)
  const textStyle = CATEGORY_TEXT[score.category] ?? 'text-slate-300'

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
      <div
        data-testid="score-gauge"
        className="relative size-36 shrink-0"
        role="img"
        aria-label={`Anomaly Indicator Score ${score.score} out of 100, ${CATEGORY_LABELS[score.category] ?? score.category}`}
      >
        <svg viewBox="0 0 128 128" className="size-full -rotate-90">
          <circle
            cx="64"
            cy="64"
            r={RADIUS}
            fill="none"
            strokeWidth="10"
            className="stroke-slate-800"
          />
          <circle
            cx="64"
            cy="64"
            r={RADIUS}
            fill="none"
            strokeWidth="10"
            stroke={color}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={dashOffset}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span data-testid="score-value" className={`text-3xl font-bold ${textStyle}`}>
            {score.score}
          </span>
          <span className="text-xs text-slate-500">/ 100</span>
        </div>
      </div>

      <div className="min-w-0 flex-1 space-y-4">
        <div>
          <h3 className="text-sm font-semibold text-slate-100">
            Anomaly Indicator Score
          </h3>
          <p
            data-testid="score-category"
            className={`text-sm font-medium capitalize ${textStyle}`}
          >
            {CATEGORY_LABELS[score.category] ?? score.category}
          </p>
        </div>

        <ul data-testid="score-factors" className="space-y-3">
          {score.factors.map((factor) => (
            <li key={factor.name} className="text-sm">
              <div className="flex items-center justify-between gap-2">
                <span className="text-slate-300">{factor.label}</span>
                <span className="font-mono text-xs text-slate-400">
                  {factor.points}/{factor.max_points}
                </span>
              </div>
              <p className="mt-0.5 text-xs text-slate-500">{factor.reason}</p>
            </li>
          ))}
        </ul>

        <p className="text-xs text-slate-600">
          The score reflects independent technical indicators with their reasons.
          It is not a probability of tampering and requires expert review.
        </p>
      </div>
    </div>
  )
}
