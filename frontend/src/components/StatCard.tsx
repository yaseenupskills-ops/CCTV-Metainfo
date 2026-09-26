import type { ReactNode } from 'react'

interface StatCardProps {
  label: string
  value: number | string
  accent?: string
  hint?: string
  icon?: ReactNode
}

export default function StatCard({
  label,
  value,
  accent = 'text-accent',
  hint,
  icon,
}: StatCardProps) {
  return (
    <div className="rounded-xl border border-edge bg-panel p-5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">
          {label}
        </span>
        {icon}
      </div>
      <div className={`mt-3 text-3xl font-semibold tabular-nums ${accent}`}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-slate-500">{hint}</div> : null}
    </div>
  )
}
