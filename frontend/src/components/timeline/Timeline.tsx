import { useState } from 'react'

import type { TimelineEvent, TimelineSegment } from '../../types'
import { formatDuration } from '../../utils/format'

const SEVERITY_STYLES: Record<string, string> = {
  low: 'bg-warn',
  medium: 'bg-warn',
  high: 'bg-bad',
  critical: 'bg-bad',
}

const SEVERITY_LABELS: Record<string, string> = {
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
}

interface TimelineProps {
  segments: TimelineSegment[]
  events: TimelineEvent[]
  duration: number | null
}

function severityStyle(severity: string | null): string {
  return SEVERITY_STYLES[severity ?? ''] ?? 'bg-warn'
}

function Metrics({ metrics }: { metrics: Record<string, number> }) {
  const entries = Object.entries(metrics)
  if (entries.length === 0) return <p className="text-sm text-slate-500">No metrics recorded.</p>
  return (
    <div className="grid grid-cols-2 gap-3">
      {entries.map(([key, value]) => (
        <div key={key}>
          <dt className="text-xs uppercase tracking-wider text-slate-500">{key}</dt>
          <dd className="font-mono text-sm text-slate-200">{value}</dd>
        </div>
      ))}
    </div>
  )
}

function EventDrawer({ event }: { event: TimelineEvent }) {
  return (
    <div
      data-testid="timeline-drawer"
      className="mt-4 rounded-xl border border-edge bg-panel p-5"
    >
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h3 className="text-sm font-semibold text-slate-100">Potential anomaly</h3>
        <span className="rounded-full border border-bad/30 bg-bad/15 px-2.5 py-0.5 text-xs font-medium text-bad capitalize">
          {SEVERITY_LABELS[event.severity] ?? event.severity}
        </span>
        <span className="font-mono text-xs text-accent">
          {formatDuration(event.timestamp)} ({event.timestamp.toFixed(2)}s)
        </span>
      </div>

      <dl className="space-y-4">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-500">Detection</dt>
            <dd className="text-sm text-slate-200">{event.detection_method}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-500">Diff score</dt>
            <dd className="font-mono text-sm text-slate-200">
              {event.diff_score.toFixed(4)}
            </dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-500">Prev frame</dt>
            <dd className="font-mono text-sm text-slate-200">{event.prev_frame ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wider text-slate-500">Current frame</dt>
            <dd className="font-mono text-sm text-slate-200">{event.current_frame ?? '—'}</dd>
          </div>
        </div>

        <div>
          <dt className="mb-2 text-xs uppercase tracking-wider text-slate-500">
            Frame-difference metrics
          </dt>
          <dd>
            <Metrics metrics={event.metrics} />
          </dd>
        </div>
      </dl>
    </div>
  )
}

export default function Timeline({
  segments,
  events,
  duration,
}: TimelineProps) {
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null)

  if (segments.length === 0) {
    return (
      <div className="rounded-xl border border-edge bg-panel p-8 text-center text-sm text-slate-500">
        No timeline data yet. Run a scene-change analysis to populate it.
      </div>
    )
  }

  const total =
    duration && duration > 0
      ? duration
      : events.length > 0
        ? Math.max(...events.map((event) => event.timestamp))
        : 1
  const pct = (value: number) => `${Math.min(100, Math.max(0, (value / total) * 100))}%`
  const selectedEvent =
    selectedIndex !== null && events[selectedIndex] ? events[selectedIndex] : null

  return (
    <div>
      <div
        data-testid="timeline-track"
        className="relative h-9 w-full overflow-hidden rounded-lg border border-edge bg-surface"
      >
        {segments.map((segment, index) => {
          if (segment.kind === 'normal') {
            return (
              <div
                key={`normal-${index}`}
                data-testid="timeline-segment"
                className="absolute inset-y-0 bg-accent/30"
                style={{ left: pct(segment.start), width: pct(segment.end - segment.start) }}
              />
            )
          }
          return (
            <button
              key={`anomaly-${index}`}
              type="button"
              data-testid="timeline-anomaly"
              aria-label={`Potential anomaly at ${formatDuration(segment.start)}`}
              onClick={() => setSelectedIndex(segment.event_index ?? 0)}
              className={`absolute inset-y-0 z-10 w-2.5 -translate-x-1/2 cursor-pointer border border-black/40 ${severityStyle(
                segment.severity,
              )}`}
              style={{ left: pct(segment.start) }}
            />
          )
        })}
      </div>

      <div className="mt-1 flex justify-between text-xs text-slate-500">
        <span>0:00</span>
        <span>{formatDuration(duration)}</span>
      </div>

      <div className="mt-2 flex items-center gap-4 text-xs text-slate-500">
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-sm bg-accent/30" />
          Normal
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span className="inline-block size-2.5 rounded-sm bg-warn" />
          Potential anomaly
        </span>
      </div>

      {selectedEvent && <EventDrawer event={selectedEvent} />}
    </div>
  )
}
