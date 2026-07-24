import { FileText } from 'lucide-react'
import type { Source } from '../../types/rag'

export function SourceCard({ source, index, highlighted = false }: { source: Source; index: number; highlighted?: boolean }) {
  return <article className={`rounded-2xl border bg-stone-50 p-4 transition ${highlighted ? 'border-emerald-500 ring-2 ring-emerald-200' : 'border-stone-200'}`}>
    <div className="mb-2 flex items-center gap-2 text-sm font-semibold text-emerald-800"><FileText size={16} /><span>[{index + 1}] {source.source} · page {source.page}</span></div>
    <p className="line-clamp-3 text-sm leading-6 text-stone-600">{source.text}</p>
  </article>
}
