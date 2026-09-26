import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'

import { getEvidenceTimeline, listEvidence, runAnalysis } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import Timeline from '../components/timeline/Timeline'
import type { EvidenceTimeline } from '../types'

function isRunning(timeline: EvidenceTimeline | undefined): boolean {
  return (
    timeline?.analysis_status === 'queued' ||
    timeline?.analysis_status === 'processing'
  )
}

export default function TimelinePage() {
  const queryClient = useQueryClient()
  const [evidenceId, setEvidenceId] = useState<string>('')

  const { data: evidencePage } = useQuery({
    queryKey: ['evidence', 'list', { page_size: 100 }],
    queryFn: () => listEvidence({ page: 1, page_size: 100 }),
  })
  const evidenceItems = evidencePage?.items ?? []

  const timelineQuery = useQuery({
    queryKey: ['evidence', evidenceId, 'timeline'],
    queryFn: () => getEvidenceTimeline(evidenceId),
    enabled: Boolean(evidenceId),
    refetchInterval: (query) =>
      isRunning(query.state.data) ? 2000 : false,
  })

  const runSceneChange = useMutation({
    mutationFn: () =>
      runAnalysis(evidenceId, {
        analysis_type: 'scene_change',
        sampling_rate: 1,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidence', evidenceId, 'timeline'] })
    },
  })

  const timeline = timelineQuery.data
  const hasAnalysis = Boolean(timeline?.analysis_id)

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">Timeline</h1>
          <p className="mt-1 text-sm text-slate-500">
            Frame-difference anomalies across the video. Markers are potential
            indicators, not tampering verdicts.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <label className="flex items-center gap-3">
          <span className="text-sm text-slate-400">Evidence</span>
          <select
            data-testid="evidence-select"
            value={evidenceId}
            onChange={(event) => setEvidenceId(event.target.value)}
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
          >
            <option value="">Select an evidence…</option>
            {evidenceItems.map((item) => (
              <option key={item.id} value={item.id}>
                {item.evidence_number} — {item.original_filename}
              </option>
            ))}
          </select>
        </label>

        {evidenceId && hasAnalysis && timeline?.analysis_status ? (
          <StatusBadge status={timeline.analysis_status} />
        ) : null}

        {evidenceId && !hasAnalysis && (
          <button
            type="button"
            data-testid="run-analysis"
            onClick={() => runSceneChange.mutate()}
            disabled={runSceneChange.isPending}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:opacity-50"
          >
            {runSceneChange.isPending ? 'Running…' : 'Run scene-change analysis'}
          </button>
        )}
      </div>

      {runSceneChange.isError && (
        <p className="text-sm text-bad">
          Analysis failed: {(runSceneChange.error as Error).message}
        </p>
      )}

      {evidenceId && timelineQuery.isLoading && (
        <p className="text-sm text-slate-400">Loading timeline…</p>
      )}
      {evidenceId && timelineQuery.isError && (
        <p className="text-sm text-bad">Failed to load timeline.</p>
      )}

      {evidenceId && timeline && !timelineQuery.isError && (
        <Timeline
          segments={timeline.segments}
          events={timeline.events}
          duration={timeline.duration}
        />
      )}

      {!evidenceId && (
        <div className="rounded-xl border border-edge bg-panel p-10 text-center text-sm text-slate-500">
          Select an evidence to view its reconstruction timeline.
        </div>
      )}
    </div>
  )
}
