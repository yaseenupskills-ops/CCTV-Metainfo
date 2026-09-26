import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { getDashboardStats } from '../api/client'
import EvidenceTable from '../components/EvidenceTable'
import StatCard from '../components/StatCard'
import type { EvidenceStatus } from '../types'
import { formatDateTime } from '../utils/format'

const STATUS_ORDER: EvidenceStatus[] = [
  'uploaded',
  'hashed',
  'metadata_extracted',
  'analyzed',
  'archived',
  'deleted',
]

function maxByStatus(byStatus: Record<EvidenceStatus, number>): number {
  return Math.max(1, ...Object.values(byStatus))
}

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: getDashboardStats,
  })

  if (isLoading) return <p className="text-slate-400">Loading dashboard…</p>
  if (isError || !data) {
    return <p className="text-bad">Failed to load dashboard data.</p>
  }

  const maxCount = maxByStatus(data.evidence.by_status)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-100">Dashboard</h1>
        <Link
          to="/upload"
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft"
        >
          Upload Evidence
        </Link>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard label="Total Cases" value={data.cases.total} accent="text-accent" />
        <StatCard
          label="Total Evidence"
          value={data.evidence.total}
          hint={`${(data.evidence.total_size / 1024 / 1024).toFixed(1)} MB stored`}
          accent="text-info"
        />
        <StatCard
          label="Analyses Completed"
          value={data.analyses.completed}
          accent="text-ok"
        />
        <StatCard label="Pending Analyses" value={data.analyses.pending} accent="text-warn" />
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="space-y-6 xl:col-span-2">
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Recent Evidence
            </h2>
            <EvidenceTable
              items={data.recent_evidence}
              emptyMessage="No evidence yet."
            />
          </section>

          <section className="rounded-xl border border-edge bg-panel p-5">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
              Evidence by Status
            </h2>
            <div className="space-y-3">
              {STATUS_ORDER.map((status) => (
                <div key={status} className="flex items-center gap-3">
                  <span className="w-36 shrink-0 text-xs capitalize text-slate-400">
                    {status.replaceAll('_', ' ')}
                  </span>
                  <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface">
                    <div
                      className="h-full rounded-full bg-accent"
                      style={{
                        width: `${((data.evidence.by_status[status] ?? 0) / maxCount) * 100}%`,
                      }}
                    />
                  </div>
                  <span className="w-8 shrink-0 text-right text-xs tabular-nums text-slate-300">
                    {data.evidence.by_status[status] ?? 0}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>

        <section className="rounded-xl border border-edge bg-panel p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
            Recent Activity
          </h2>
          <ol className="space-y-3">
            {data.recent_activity.length === 0 ? (
              <li className="text-sm text-slate-500">No recent activity.</li>
            ) : (
              data.recent_activity.map((entry) => (
                <li key={entry.id} className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate font-mono text-xs text-accent">
                      {entry.action}
                    </div>
                    <div className="text-xs text-slate-500">
                      {entry.entity_type}
                      {entry.details && Object.keys(entry.details).length > 0
                        ? ` · ${String(Object.values(entry.details)[0])}`
                        : ''}
                    </div>
                  </div>
                  <div className="shrink-0 text-xs text-slate-500">
                    {formatDateTime(entry.timestamp)}
                  </div>
                </li>
              ))
            )}
          </ol>
        </section>
      </div>
    </div>
  )
}
