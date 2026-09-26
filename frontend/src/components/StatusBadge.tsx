const STATUS_STYLES: Record<string, string> = {
  open: 'bg-ok/15 text-ok border-ok/30',
  closed: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  archived: 'bg-warn/15 text-warn border-warn/30',
  uploaded: 'bg-slate-500/15 text-slate-300 border-slate-500/30',
  hashed: 'bg-accent/15 text-accent border-accent/30',
  metadata_extracted: 'bg-info/15 text-info border-info/30',
  analyzed: 'bg-ok/15 text-ok border-ok/30',
  deleted: 'bg-bad/15 text-bad border-bad/30',
  queued: 'bg-warn/15 text-warn border-warn/30',
  processing: 'bg-accent/15 text-accent border-accent/30',
  completed: 'bg-ok/15 text-ok border-ok/30',
  failed: 'bg-bad/15 text-bad border-bad/30',
}

function humanize(value: string): string {
  return value.replaceAll('_', ' ')
}

export default function StatusBadge({ status }: { status: string }) {
  const style = STATUS_STYLES[status] ?? 'bg-slate-500/15 text-slate-300 border-slate-500/30'
  return (
    <span
      data-testid="status-badge"
      className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-medium capitalize ${style}`}
    >
      {humanize(status)}
    </span>
  )
}
