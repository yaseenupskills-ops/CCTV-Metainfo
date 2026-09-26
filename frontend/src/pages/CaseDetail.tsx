import { useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'

import { getCase } from '../api/client'
import StatusBadge from '../components/StatusBadge'

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>()

  const { data, isLoading, isError } = useQuery({
    queryKey: ['case', id],
    queryFn: () => getCase(id!),
    enabled: !!id,
  })

  if (isLoading) {
    return <p className="text-slate-400">Loading case…</p>
  }

  if (isError || !data) {
    return <p className="text-bad">Failed to load case.</p>
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-100">{String(data.title)}</h1>
          <p className="mt-1 font-mono text-sm text-slate-400">{String(data.case_number)}</p>
        </div>
        <StatusBadge status={String(data.status)} />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="rounded-xl border border-edge bg-panel p-5">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Description
          </span>
          <p className="mt-2 text-sm text-slate-200">
            {String(data.description || 'No description provided.')}
          </p>
        </div>

        <div className="rounded-xl border border-edge bg-panel p-5">
          <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
            Details
          </span>
          <dl className="mt-2 space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-slate-400">Investigator ID</dt>
              <dd className="font-mono text-xs text-slate-300">
                {data.investigator_id ? String(data.investigator_id) : '—'}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Created</dt>
              <dd className="text-slate-300">
                {new Date(data.created_at).toLocaleString()}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-slate-400">Updated</dt>
              <dd className="text-slate-300">
                {new Date(data.updated_at).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>
      </div>
    </div>
  )
}
