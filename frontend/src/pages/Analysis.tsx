import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { listEvidence } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import {
  useEvidenceAnalyses,
  useExtractMetadata,
  useStartAnalysis,
} from '../hooks/useAnalysis'
import type { Analysis, AnalysisStatus } from '../types'
import { formatDateTime } from '../utils/format'

const ACTIVE_STATUSES: AnalysisStatus[] = ['queued', 'processing']

// List rows only carry the server-derived `summary`; the full `result` is
// present on the detail response. Read whichever is available so the column is
// populated either way.
function resultSummary(analysis: Analysis): string {
  const source = analysis.summary ?? analysis.result
  if (!source) return '—'
  if (analysis.analysis_type === 'scene_change') {
    // `summary` carries a pre-counted number; `result` carries the array.
    const events = source.events
    const count = typeof events === 'number' ? events : Array.isArray(events) ? events.length : 0
    return `${count} event${count === 1 ? '' : 's'}`
  }
  const frames = source.frames_sampled
  return `${String(frames ?? '?')} frame${frames === 1 ? '' : 's'} sampled`
}

function formatParams(params: Record<string, unknown>): string {
  const entries = Object.entries(params)
  if (entries.length === 0) return '—'
  return entries.map(([key, value]) => `${key}=${String(value)}`).join(', ')
}

export default function Analysis() {
  const [selectedId, setSelectedId] = useState('')

  const { data: evidencePage } = useQuery({
    queryKey: ['evidence', { page: 1, page_size: 100 }],
    queryFn: () => listEvidence({ page: 1, page_size: 100 }),
  })

  const evidenceItems = evidencePage?.items ?? []
  const selectedEvidence = evidenceItems.find((item) => item.id === selectedId) ?? evidenceItems[0]
  const evidenceId = selectedEvidence?.id

  const analysesQuery = useEvidenceAnalyses(evidenceId)
  const startAnalysis = useStartAnalysis(evidenceId)
  const metadataMutation = useExtractMetadata(evidenceId)

  const activeCount = (analysesQuery.data ?? []).filter((analysis) =>
    ACTIVE_STATUSES.includes(analysis.status),
  ).length

  const busy = activeCount > 0 || startAnalysis.isPending || metadataMutation.isPending

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Analysis</h1>
        <p className="mt-1 text-sm text-slate-400">
          Queue background jobs for an evidence. Status refreshes automatically while jobs run.
        </p>
      </div>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="flex flex-col gap-1.5 lg:w-96">
            <label htmlFor="evidence-picker" className="text-sm text-slate-300">
              Evidence
            </label>
            <select
              id="evidence-picker"
              value={selectedEvidence?.id ?? ''}
              onChange={(event) => setSelectedId(event.target.value)}
              className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
            >
              {evidenceItems.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.evidence_number} — {item.original_filename}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => metadataMutation.mutate()}
              disabled={!evidenceId || busy}
              className="rounded-lg border border-edge bg-surface px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              Extract metadata
            </button>
            <button
              type="button"
              onClick={() => startAnalysis.mutate({ analysis_type: 'frame_sampling', sampling_rate: 1 })}
              disabled={!evidenceId || busy}
              className="rounded-lg border border-edge bg-surface px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
            >
              Frame sampling
            </button>
            <button
              type="button"
              onClick={() =>
                startAnalysis.mutate({
                  analysis_type: 'scene_change',
                  sampling_rate: 1,
                  threshold: 0.5,
                })
              }
              disabled={!evidenceId || busy}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-40"
            >
              Scene change
            </button>
          </div>
        </div>

        {selectedEvidence ? (
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-slate-400">
            <span className="text-slate-300">{selectedEvidence.evidence_number}</span>
            <StatusBadge status={selectedEvidence.status} />
            <Link
              to={`/evidence/${selectedEvidence.id}`}
              className="text-accent hover:underline"
            >
              View detail →
            </Link>
            {activeCount > 0 ? (
              <span className="animate-pulse text-warn">Running {activeCount} job(s)…</span>
            ) : null}
          </div>
        ) : (
          <p className="mt-4 text-sm text-slate-500">No evidence available to analyze.</p>
        )}
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Analysis History
        </h2>
        {analysesQuery.isLoading ? (
          <p className="text-sm text-slate-500">Loading analyses…</p>
        ) : (analysesQuery.data ?? []).length === 0 ? (
          <p className="text-sm text-slate-500">
            No analyses have been run on this evidence yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-edge text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-3 py-2 font-medium">Type</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Parameters</th>
                  <th className="px-3 py-2 font-medium">Started</th>
                  <th className="px-3 py-2 font-medium">Completed</th>
                  <th className="px-3 py-2 font-medium">Result</th>
                </tr>
              </thead>
              <tbody>
                {(analysesQuery.data ?? []).map((analysis) => (
                  <tr key={analysis.id} className="border-b border-edge/60 last:border-0">
                    <td className="px-3 py-2 font-mono text-xs text-accent">
                      {analysis.analysis_type}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={analysis.status} />
                    </td>
                    <td className="px-3 py-2 font-mono text-xs text-slate-400">
                      {formatParams(analysis.params)}
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {formatDateTime(analysis.started_at)}
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {formatDateTime(analysis.completed_at)}
                    </td>
                    <td className="px-3 py-2 text-slate-300">
                      {analysis.status === 'failed'
                        ? (analysis.error_message ?? 'Failed')
                        : resultSummary(analysis)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
