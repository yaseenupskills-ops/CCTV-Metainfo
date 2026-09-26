import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { createCase, listCases } from '../api/client'
import StatusBadge from '../components/StatusBadge'
import type { CaseSummary } from '../types'

export default function Cases() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [showCreate, setShowCreate] = useState(false)
  const [formTitle, setFormTitle] = useState('')
  const [formNumber, setFormNumber] = useState('')
  const [formDescription, setFormDescription] = useState('')
  const [formError, setFormError] = useState('')

  const { data, isLoading, isError } = useQuery({
    queryKey: ['cases', { search, page }],
    queryFn: () => listCases({ search, page, page_size: 20 }),
  })

  const createMutation = useMutation({
    mutationFn: createCase,
    onSuccess: (created) => {
      queryClient.invalidateQueries({ queryKey: ['cases'] })
      setShowCreate(false)
      setFormTitle('')
      setFormNumber('')
      setFormDescription('')
      setFormError('')
      navigate(`/cases/${created.id}`)
    },
    onError: (err: Error) => {
      setFormError(err.message || 'Failed to create case')
    },
  })

  const handleCreate = () => {
    if (!formTitle.trim()) {
      setFormError('Title is required')
      return
    }
    setFormError('')
    createMutation.mutate({
      title: formTitle.trim(),
      case_number: formNumber.trim() || undefined,
      description: formDescription.trim() || undefined,
    })
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-slate-100">Cases</h1>
        <button
          onClick={() => setShowCreate(true)}
          className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/80"
        >
          New Case
        </button>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <input
          data-testid="cases-search"
          value={search}
          onChange={(event) => {
            setSearch(event.target.value)
            setPage(1)
          }}
          placeholder="Search case number or title…"
          className="w-72 rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
        />
      </div>

      {isLoading ? (
        <p className="text-slate-400">Loading cases…</p>
      ) : isError || !data ? (
        <p className="text-bad">Failed to load cases.</p>
      ) : data.items.length === 0 ? (
        <div className="rounded-xl border border-edge bg-panel p-10 text-center text-slate-400">
          No cases found. Create one to get started.
        </div>
      ) : (
        <>
          <div className="overflow-hidden rounded-xl border border-edge bg-panel">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-edge bg-surface/50 text-xs uppercase tracking-wider text-slate-400">
                  <th className="px-4 py-3">Case Number</th>
                  <th className="px-4 py-3">Title</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Created</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((c: CaseSummary) => (
                  <tr
                    key={c.id}
                    data-testid="case-row"
                    onClick={() => navigate(`/cases/${c.id}`)}
                    className="cursor-pointer border-b border-edge/50 transition-colors hover:bg-surface/30 last:border-0"
                  >
                    <td className="px-4 py-3 font-mono text-xs text-slate-300">
                      {c.case_number}
                    </td>
                    <td className="px-4 py-3 text-slate-100">{c.title}</td>
                    <td className="px-4 py-3">
                      <StatusBadge status={c.status} />
                    </td>
                    <td className="px-4 py-3 text-slate-400">
                      {new Date(c.created_at).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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

      {showCreate && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60">
          <div className="w-full max-w-lg rounded-xl border border-edge bg-panel p-6 shadow-xl">
            <h2 className="mb-4 text-lg font-semibold text-slate-100">Create New Case</h2>
            <div className="space-y-4">
              <div>
                <label className="mb-1 block text-sm text-slate-400">Title *</label>
                <input
                  data-testid="case-title-input"
                  value={formTitle}
                  onChange={(e) => setFormTitle(e.target.value)}
                  placeholder="e.g. Suspicious activity at Warehouse 7"
                  className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm text-slate-400">Case Number</label>
                <input
                  data-testid="case-number-input"
                  value={formNumber}
                  onChange={(e) => setFormNumber(e.target.value)}
                  placeholder="e.g. 2026-0001"
                  className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-sm text-slate-400">Description</label>
                <textarea
                  data-testid="case-description-input"
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  rows={3}
                  placeholder="Brief description of the case…"
                  className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
                />
              </div>
              {formError && <p className="text-sm text-bad">{formError}</p>}
            </div>
            <div className="mt-6 flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowCreate(false)
                  setFormError('')
                }}
                className="rounded-lg border border-edge bg-surface px-4 py-2 text-sm text-slate-300 hover:bg-surface/80"
              >
                Cancel
              </button>
              <button
                data-testid="case-create-btn"
                onClick={handleCreate}
                disabled={createMutation.isPending}
                className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white hover:bg-accent/80 disabled:opacity-50"
              >
                {createMutation.isPending ? 'Creating…' : 'Create Case'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
