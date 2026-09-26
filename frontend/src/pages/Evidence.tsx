import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { listEvidence } from '../api/client'
import EvidenceTable from '../components/EvidenceTable'
import type { EvidenceListItem } from '../types'

export default function Evidence() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [page, setPage] = useState(1)

  const { data, isLoading, isError } = useQuery({
    queryKey: ['evidence', { search, status, page }],
    queryFn: () => listEvidence({ search, status, page, page_size: 20 }),
  })

  const handleRowClick = (item: EvidenceListItem) => navigate(`/evidence/${item.id}`)

  return (
    <div className="space-y-5">
      <h1 className="text-xl font-semibold text-slate-100">Evidence</h1>

      <div className="flex flex-wrap items-center gap-3">
        <input
          data-testid="evidence-search"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(1)
          }}
          placeholder="Search evidence number, filename, case…"
          className="w-72 rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
        />
        <select
          data-testid="evidence-status-filter"
          value={status}
          onChange={(event) => {
            setStatus(event.target.value)
            setPage(1)
          }}
          className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
        >
          <option value="">All statuses</option>
          <option value="uploaded">Uploaded</option>
          <option value="hashed">Hashed</option>
          <option value="metadata_extracted">Metadata extracted</option>
          <option value="analyzed">Analyzed</option>
          <option value="archived">Archived</option>
          <option value="deleted">Deleted</option>
        </select>
      </div>

      {isLoading ? (
        <p className="text-slate-400">Loading evidence…</p>
      ) : isError || !data ? (
        <p className="text-bad">Failed to load evidence.</p>
      ) : (
        <>
          <EvidenceTable items={data.items} onRowClick={handleRowClick} />
          <div className="flex items-center justify-between text-sm text-slate-400">
            <span>
              Page {data.page} of {Math.max(data.total_pages, 1)} · {data.total} total
            </span>
            <div className="flex gap-2">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="rounded-lg border border-edge bg-surface px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Prev
              </button>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= data.total_pages}
                className="rounded-lg border border-edge bg-surface px-3 py-1.5 text-sm disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
