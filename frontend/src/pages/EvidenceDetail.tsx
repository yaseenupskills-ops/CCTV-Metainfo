import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { getEvidence, getEvidenceAnomalyScore } from '../api/client'
import ScoreGauge from '../components/analysis/ScoreGauge'
import StatusBadge from '../components/StatusBadge'
import {
  useEvidenceAnalyses,
  useExtractMetadata,
  useStartAnalysis,
} from '../hooks/useAnalysis'
import {
  formatDateTime,
  formatDuration,
  formatFileSize,
} from '../utils/format'

function Field({ label, value }: { label: string; value: string | number | null | undefined }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="text-sm text-slate-200">{value ?? '—'}</dd>
    </div>
  )
}

const ACTIVE_STATUSES = new Set(['queued', 'processing'])

export default function EvidenceDetail() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, isError } = useQuery({
    queryKey: ['evidence', id],
    queryFn: () => getEvidence(id!),
    enabled: Boolean(id),
  })

  const { data: anomalyScore } = useQuery({
    queryKey: ['evidence', id, 'anomaly-score'],
    queryFn: () => getEvidenceAnomalyScore(id!),
    enabled: Boolean(id),
  })

  const analysesQuery = useEvidenceAnalyses(id)
  const startAnalysis = useStartAnalysis(id)
  const metadataMutation = useExtractMetadata(id)
  const analyses = analysesQuery.data ?? []
  const running = analyses.some((analysis) => ACTIVE_STATUSES.has(analysis.status))

  if (isLoading) return <p className="text-slate-400">Loading evidence…</p>
  if (isError || !data) return <p className="text-bad">Failed to load evidence.</p>

  const meta = data.video_metadata

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/evidence" className="text-sm text-accent hover:underline">
          ← Evidence
        </Link>
        <h1 className="text-xl font-semibold text-slate-100">
          {data.evidence_number}
        </h1>
        <StatusBadge status={data.status} />
      </div>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Overview
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Filename" value={data.original_filename} />
          <Field label="Size" value={formatFileSize(data.file_size)} />
          <Field label="MIME type" value={data.mime_type} />
          <Field label="Uploaded" value={formatDateTime(data.uploaded_at)} />
        </dl>
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Integrity
        </h2>
        <dl className="grid grid-cols-1 gap-4">
          <Field label="SHA-256" value={data.sha256} />
          <Field label="SHA-512" value={data.sha512} />
          <Field
            label="Calculated at"
            value={formatDateTime(data.hash_calculated_at)}
          />
        </dl>
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Video Information
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field
            label="Resolution"
            value={
              meta?.width && meta?.height ? `${meta.width} × ${meta.height}` : null
            }
          />
          <Field label="Duration" value={formatDuration(meta?.duration)} />
          <Field
            label="Frame rate"
            value={meta?.frame_rate ? `${meta.frame_rate.toFixed(2)} fps` : null}
          />
          <Field label="Video codec" value={meta?.video_codec} />
          <Field label="Audio codec" value={meta?.audio_codec} />
          <Field label="Pixel format" value={meta?.pixel_format} />
          <Field label="Bitrate" value={meta?.bitrate} />
          <Field label="Frames" value={meta?.frame_count} />
        </dl>
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Metadata
        </h2>
        <dl className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Field label="Container format" value={meta?.container_format} />
          <Field label="Encoder" value={meta?.encoder} />
          <Field label="Stream count" value={meta?.stream_count} />
          <Field label="Creation time" value={formatDateTime(meta?.creation_time)} />
        </dl>
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Anomaly Indicator Score
        </h2>
        {anomalyScore ? (
          <ScoreGauge score={anomalyScore} />
        ) : (
          <p className="text-sm text-slate-500">Loading anomaly score…</p>
        )}
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            Background Jobs
          </h2>
          {running ? <span className="animate-pulse text-sm text-warn">Running…</span> : null}
        </div>
        <div className="flex flex-wrap gap-3">
          <button
            type="button"
            onClick={() => metadataMutation.mutate()}
            disabled={metadataMutation.isPending}
            className="rounded-lg border border-edge bg-surface px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
            {metadataMutation.isPending ? 'Queuing…' : 'Extract metadata'}
          </button>
          <button
            type="button"
            onClick={() => startAnalysis.mutate({ analysis_type: 'frame_sampling', sampling_rate: 1 })}
            disabled={startAnalysis.isPending}
            className="rounded-lg border border-edge bg-surface px-4 py-2 text-sm font-medium text-slate-200 transition-colors hover:border-accent disabled:cursor-not-allowed disabled:opacity-40"
          >
            {startAnalysis.isPending ? 'Queuing…' : 'Frame sampling'}
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
            disabled={startAnalysis.isPending}
            className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-40"
          >
            {startAnalysis.isPending ? 'Queuing…' : 'Scene change'}
          </button>
        </div>
      </section>

      <section className="rounded-xl border border-edge bg-panel p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Analysis
        </h2>
        {analyses.length === 0 ? (
          <p className="text-sm text-slate-500">No analyses have been run on this evidence.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-edge text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-3 py-2 font-medium">Type</th>
                  <th className="px-3 py-2 font-medium">Status</th>
                  <th className="px-3 py-2 font-medium">Started</th>
                  <th className="px-3 py-2 font-medium">Completed</th>
                </tr>
              </thead>
              <tbody>
                {analyses.map((analysis) => (
                  <tr key={analysis.id} className="border-b border-edge/60 last:border-0">
                    <td className="px-3 py-2 font-mono text-xs text-accent">
                      {analysis.analysis_type}
                    </td>
                    <td className="px-3 py-2">
                      <StatusBadge status={analysis.status} />
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {formatDateTime(analysis.started_at)}
                    </td>
                    <td className="px-3 py-2 text-slate-400">
                      {formatDateTime(analysis.completed_at)}
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
