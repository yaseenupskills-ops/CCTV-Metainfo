import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'

import { api } from '../api/client'

export default function Upload() {
  const navigate = useNavigate()
  const [caseId, setCaseId] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<string | null>(null)

  const canSubmit = Boolean(caseId.trim() && file)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!canSubmit) return
    setUploading(true)
    setError(null)
    setResult(null)
    try {
      const form = new FormData()
      form.append('case_id', caseId.trim())
      form.append('file', file!)
      const { data } = await api.post('/evidence/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setResult(`Uploaded ${data.original_filename} (${data.evidence_number})`)
      setTimeout(() => navigate(`/evidence/${data.id}`), 1200)
    } catch (err) {
      const detail =
        typeof err === 'object' && err !== null && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data
              ?.detail
          : undefined
      setError(detail ?? 'Upload failed. Check the case ID and file type.')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-5">
      <h1 className="text-xl font-semibold text-slate-100">Upload Evidence</h1>

      <form onSubmit={handleSubmit} className="space-y-4 rounded-xl border border-edge bg-panel p-6">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="case-id" className="text-sm text-slate-300">
            Case ID
          </label>
          <input
            id="case-id"
            value={caseId}
            onChange={(event) => setCaseId(event.target.value)}
            placeholder="UUID of the case (e.g. 3f2c…)"
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:border-accent focus:outline-none"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="file" className="text-sm text-slate-300">
            Video file
          </label>
          <input
            id="file"
            type="file"
            accept=".mp4,.mov,.avi,.mkv,video/*"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="rounded-lg border border-edge bg-surface px-3 py-2 text-sm text-slate-200 file:mr-3 file:rounded-md file:border-0 file:bg-accent file:px-3 file:py-1.5 file:text-sm file:text-white"
          />
        </div>

        {error ? <p className="text-sm text-bad">{error}</p> : null}
        {result ? <p className="text-sm text-ok">{result}</p> : null}

        <button
          type="submit"
          disabled={!canSubmit || uploading}
          className="w-full rounded-lg bg-accent px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-soft disabled:cursor-not-allowed disabled:opacity-40"
        >
          {uploading ? 'Uploading…' : 'Upload'}
        </button>
      </form>
    </div>
  )
}
