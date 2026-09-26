export default function PagePlaceholder({ title, note }: { title: string; note: string }) {
  return (
    <div>
      <h1 className="text-xl font-semibold text-slate-100">{title}</h1>
      <p className="mt-1 text-sm text-slate-500">{note}</p>
      <div className="mt-6 rounded-xl border border-dashed border-edge bg-panel p-16 text-center text-sm text-slate-500">
        This section is planned for a later phase and will be connected to the backend API.
      </div>
    </div>
  )
}
