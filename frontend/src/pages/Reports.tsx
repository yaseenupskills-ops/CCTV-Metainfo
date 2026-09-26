import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import { listCases, listEvidence, generateReport, listReports, downloadReport } from '../api/client'
import type { Report } from '../types'
import { formatDateTime } from '../utils/format'

export default function Reports() {
  const queryClient = useQueryClient()

  const { data: cases, isLoading: loadingCases } = useQuery({
    queryKey: ['cases'],
    queryFn: () => listCases({ page_size: 100 }),
  })

  const { data: evidences, isLoading: loadingEvidences } = useQuery({
    queryKey: ['evidences'],
    queryFn: () => listEvidence({ page_size: 100 }),
  })

  const { data: reports, isLoading: loadingReports, isError } = useQuery({
    queryKey: ['reports'],
    queryFn: () => listReports({ page_size: 20 }),
  })

  const [formCaseId, setFormCaseId] = useState('')
  const [formEvidenceId, setFormEvidenceId] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState<string | null>(null)
  const [genSuccess, setGenSuccess] = useState<string | null>(null)

  const createMutation = useMutation({
    mutationFn: () => generateReport({
      case_id: formCaseId,
      evidence_id: formEvidenceId ?? undefined,
      comparison_id: undefined,
    }),
    onSuccess: () => {
      setGenSuccess('Report generation started.')
      setGenError(null)
      queryClient.invalidateQueries({ queryKey: ['reports'] })
      setTimeout(() => setGenSuccess(null), 3000)
    },
    onError: (err: unknown) => {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined
      setGenError(detail ?? 'Could not generate report.')
    },
  })

  function handleCaseChange(event: any) {
    const id = event.target.value
    setFormCaseId(id)
    setFormEvidenceId(null)
  }

  function handleEvidenceChange(event: any) {
    setFormEvidenceId(event.target.value || null)
  }

  if (loadingCases || loadingEvidences || loadingReports) {
    return (
      <div className="p-6 text-slate-400">Loading…</div>
    )
  }

  return (
    <div className="mx-auto max-w-2xl p-6">
      <h1 className="text-2xl font-semibold text-slate-100 mb-6">
        Forensic Reports
      </h1>

      <div className="bg-panel rounded-xl p-5 mb-6 shadow-sm">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Generate report
        </h2>

        <form
          onSubmit={
            event => {
              event.preventDefault()
              if (formCaseId.trim()) {
                setGenerating(true)
                setGenError(null)
                createMutation.mutate()
              }
            }
          }
          className="grid grid-cols-2 gap-4"
        >
          <div>
            <label htmlFor="report-case" className="text-sm text-slate-300">
              Case
            </label>
            <select
              id="report-case"
              value={formCaseId}
              onChange={handleCaseChange}
              className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
            >
              <option value="">Select a case</option>
              {cases?.items?.map((c: any) => (
                <option key={c.id} value={c.id}>
                  {c.case_number}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label htmlFor="report-evidence" className="text-sm text-slate-300">
              Evidence
            </label>
            <select
              id="report-evidence"
              value={formEvidenceId ?? ''}
              onChange={handleEvidenceChange}
              className="w-full rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 focus:border-accent focus:outline-none"
            >
              <option value="">Select evidence</option>
              {evidences?.items?.map((e: any) => (
                <option key={e.id} value={e.id}>
                  {e.evidence_number}
                </option>
              ))}
            </select>
          </div>

          <div className="col-span-2">
            <button
              type="submit"
              disabled={generating}
              className="rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-60"
            >
              {generating ? 'Generating…' : 'Generate Report'}
            </button>
          </div>
        </form>
      </div>

      {genError && (
        <p className="mb-3 rounded-lg border border-bad/40 bg-bad/10 text-sm text-bad">{genError}</p>
      )}

      {genSuccess && (
        <p className="mb-3 rounded-lg border border-ok/40 bg-ok/10 text-sm text-ok">{genSuccess}</p>
      )}

      <div className="bg-panel rounded-xl p-5">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-slate-400">
          Generated Reports
        </h2>

        {isError || !reports?.items?.length
          ? <p className="text-slate-400">No reports found.</p>
          : (
              <table className="w-full text-left text-sm">
                <thead className="border-b border-edge text-xs uppercase tracking-wider text-slate-400">
                  <tr>
                    <th className="px-4 py-3 font-medium">ID</th>
                    <th className="px-4 py-3 font-medium">Case</th>
                    <th className="px-4 py-3 font-medium">Evidence</th>
                    <th className="px-4 py-3 font-medium">Generated</th>
                    <th className="px-4 py-3 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {reports.items.map((r: Report) => (
                    <tr key={r.id} className="border-b border-edge/60 last:border-0">
                      <td className="px-4 py-3 text-slate-200">{r.id.substring(0, 8)}…</td>
                      <td className="px-4 py-3 text-slate-300">{r.case_number || '—'}</td>
                      <td className="px-4 py-3 text-slate-300">
                        {r.evidence_number || '—'}
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {formatDateTime(r.generated_at)}
                      </td>
                      <td className="px-4 py-3">
                        <button
                          onClick={async () => {
                            try {
                              const blob = await downloadReport(r.id)
                              const url = URL.createObjectURL(blob)
                              const link = document.createElement('a')
                              link.href = url
                              link.download = `forensic-report-${r.id}.pdf`
                              document.body.appendChild(link)
                              link.click()
                              link.remove()
                              URL.revokeObjectURL(url)
                            } catch {
                              setGenError('Could not download report.')
                            }
                          }}
                          className="underline text-accent hover:text-accent-soft text-sm"
                        >
                          Download
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
      </div>
    </div>
  )
}
