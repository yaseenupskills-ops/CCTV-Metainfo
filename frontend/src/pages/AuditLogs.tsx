import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'

import { listAuditLogs } from '../api/client'
import type { AuditLog } from '../types'
import { formatDateTime } from '../utils/format'

export default function AuditLogs() {
  const [actionFilter, setActionFilter] = useState('')
  const [entityTypeFilter, setEntityTypeFilter] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['audit-logs', { action: actionFilter, entity_type: entityTypeFilter, page }],
    queryFn: () =>
      listAuditLogs({
        page,
        page_size: 20,
        action: actionFilter || undefined,
        entity_type: entityTypeFilter || undefined,
      }),
  })

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-5xl p-6">
      <h1 className="text-2xl font-semibold text-slate-100 mb-6">Audit Logs</h1>

      <div className="mb-4 flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Filter by action…"
          value={actionFilter}
          onChange={(e) => { setActionFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
        />
        <input
          type="text"
          placeholder="Filter by entity type…"
          value={entityTypeFilter}
          onChange={(e) => { setEntityTypeFilter(e.target.value); setPage(1) }}
          className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
        />
      </div>

      <div className="bg-panel rounded-xl p-5 shadow-sm">
        {isLoading ? (
          <p className="text-slate-400">Loading…</p>
        ) : isError ? (
          <p className="text-bad">Could not load audit logs.</p>
        ) : items.length === 0 ? (
          <p className="text-slate-400">No audit entries found.</p>
        ) : (
          <table className="w-full text-left text-sm">
            <thead className="border-b border-edge text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3 font-medium">Timestamp</th>
                <th className="px-4 py-3 font-medium">Action</th>
                <th className="px-4 py-3 font-medium">Entity</th>
                <th className="px-4 py-3 font-medium">User</th>
                <th className="px-4 py-3 font-medium">Details</th>
              </tr>
            </thead>
            <tbody>
              {items.map((log: AuditLog) => (
                <tr key={log.id} className="border-b border-edge/60 last:border-0">
                  <td className="px-4 py-3 text-xs text-slate-500">
                    {formatDateTime(log.timestamp)}
                  </td>
                  <td className="px-4 py-3">
                    <span className="inline-block rounded bg-surface px-2 py-0.5 font-mono text-xs text-accent">
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-300">
                    {log.entity_type}
                    {log.entity_id ? (
                      <span className="block font-mono text-xs text-slate-500">
                        {log.entity_id.substring(0, 8)}…
                      </span>
                    ) : null}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">
                    {log.user_id ? log.user_id.substring(0, 8) : 'system'}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-500">
                    {log.details ? JSON.stringify(log.details).slice(0, 80) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        {data && data.total_pages > 1 && (
          <div className="mt-4 flex items-center justify-between text-sm">
            <button
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
              className="rounded-lg border border-edge px-3 py-1.5 text-slate-300 disabled:cursor-not-allowed disabled:opacity-50 hover:border-accent"
            >
              Previous
            </button>
            <span className="text-slate-400">
              Page {data.page} of {data.total_pages}
            </span>
            <button
              disabled={page >= data.total_pages}
              onClick={() => setPage((p) => p + 1)}
              className="rounded-lg border border-edge px-3 py-1.5 text-slate-300 disabled:cursor-not-allowed disabled:opacity-50 hover:border-accent"
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
