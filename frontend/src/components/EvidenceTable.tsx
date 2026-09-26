import type { EvidenceListItem } from '../types'
import { formatDateTime, formatFileSize } from '../utils/format'
import StatusBadge from './StatusBadge'

interface EvidenceTableProps {
  items: EvidenceListItem[]
  onRowClick?: (evidence: EvidenceListItem) => void
  emptyMessage?: string
}

export default function EvidenceTable({
  items,
  onRowClick,
  emptyMessage = 'No evidence yet.',
}: EvidenceTableProps) {
  if (items.length === 0) {
    return (
      <div className="rounded-xl border border-edge bg-panel p-8 text-center text-sm text-slate-500">
        {emptyMessage}
      </div>
    )
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-edge bg-panel">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-edge text-xs uppercase tracking-wider text-slate-400">
            <th className="px-4 py-3 font-medium">Evidence #</th>
            <th className="px-4 py-3 font-medium">Filename</th>
            <th className="px-4 py-3 font-medium">Case</th>
            <th className="px-4 py-3 font-medium">Size</th>
            <th className="px-4 py-3 font-medium">Status</th>
            <th className="px-4 py-3 font-medium">Uploaded</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr
              key={item.id}
              data-testid="evidence-row"
              onClick={() => onRowClick?.(item)}
              className={`border-b border-edge/60 last:border-0 ${
                onRowClick ? 'cursor-pointer hover:bg-surface' : ''
              }`}
            >
              <td className="px-4 py-3 font-mono text-xs text-accent">
                {item.evidence_number}
              </td>
              <td className="px-4 py-3 text-slate-200">{item.original_filename}</td>
              <td className="px-4 py-3 text-slate-400">{item.case_number ?? '—'}</td>
              <td className="px-4 py-3 tabular-nums text-slate-400">
                {formatFileSize(item.file_size)}
              </td>
              <td className="px-4 py-3">
                <StatusBadge status={item.status} />
              </td>
              <td className="px-4 py-3 text-slate-400">
                {formatDateTime(item.uploaded_at)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
