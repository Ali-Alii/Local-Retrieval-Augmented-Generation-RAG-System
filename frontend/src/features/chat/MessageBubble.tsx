import { useState } from 'react'
import { Bot, ChevronDown, RefreshCw, ThumbsDown, ThumbsUp, User } from 'lucide-react'
import type { ChatMessage, ResponseVersion } from '../../types/rag'
import { FeedbackModal } from './FeedbackModal'
import { MarkdownMessage } from './MarkdownMessage'
import { SourceCard } from './SourceCard'

type Props = {
  message: ChatMessage
  busy?: boolean
  onRegenerate: (message: ChatMessage) => void
  onVersionChange: (messageId: string, versionId: string) => void
  onFeedback: (messageId: string, versionId: string, rating: 'up' | 'down', reason?: string, comment?: string) => Promise<void>
}

export function MessageBubble({ message, busy = false, onRegenerate, onVersionChange, onFeedback }: Props) {
  const assistant = message.role === 'assistant'
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [highlighted, setHighlighted] = useState<number | null>(null)
  const [feedbackOpen, setFeedbackOpen] = useState(false)
  const versions = message.versions ?? []
  const activeVersion: ResponseVersion | undefined = versions.find((version) => version.id === message.activeVersionId) ?? versions.at(-1)
  const content = activeVersion?.content ?? message.content
  const sources = activeVersion?.sources ?? []

  function showCitation(index: number) {
    setSourcesOpen(true); setHighlighted(index)
    window.setTimeout(() => setHighlighted(null), 1800)
  }

  return <article className={`flex gap-3 ${assistant ? '' : 'flex-row-reverse'}`}>
    <div className={`grid size-9 shrink-0 place-items-center rounded-xl ${assistant ? 'bg-emerald-800 text-white' : 'bg-stone-200 text-stone-700'}`}>{assistant ? <Bot size={18} /> : <User size={18} />}</div>
    <div className={`max-w-[86%] rounded-2xl px-5 py-4 ${assistant ? 'border border-stone-200 bg-white' : 'bg-emerald-700 text-white'}`}>
      {message.label && <p className={`mb-2 text-[11px] font-bold tracking-[.16em] ${assistant ? 'text-emerald-700' : 'text-emerald-100'}`}>{message.label}</p>}
      {assistant ? <MarkdownMessage content={content} sources={sources} onCitation={showCitation} /> : <p className="whitespace-pre-wrap leading-7">{content}</p>}
      {assistant && activeVersion && <><div className="mt-4 flex flex-wrap items-center gap-2 border-t border-stone-100 pt-3"><button type="button" disabled={busy} onClick={() => onRegenerate(message)} className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs font-semibold text-stone-600 hover:bg-stone-100 disabled:opacity-50"><RefreshCw size={14} />Regenerate</button><button type="button" onClick={() => void onFeedback(message.id, activeVersion.id, 'up')} className="rounded-lg p-2 text-stone-500 hover:bg-emerald-50 hover:text-emerald-700" aria-label="Helpful response"><ThumbsUp size={15} /></button><button type="button" onClick={() => setFeedbackOpen(true)} className="rounded-lg p-2 text-stone-500 hover:bg-red-50 hover:text-red-700" aria-label="Unhelpful response"><ThumbsDown size={15} /></button>{versions.length > 1 && <div className="ml-auto flex items-center gap-1"><span className="text-xs text-stone-400">Version</span><select value={activeVersion.id} onChange={(event) => onVersionChange(message.id, event.target.value)} className="rounded-lg border border-stone-200 bg-white px-2 py-1 text-xs">{versions.map((version, index) => <option key={version.id} value={version.id}>{index + 1} of {versions.length}</option>)}</select></div>}</div>{sources.length > 0 && <details open={sourcesOpen} onToggle={(event) => setSourcesOpen(event.currentTarget.open)} className="mt-3 rounded-xl border border-stone-200 bg-stone-50"><summary className="flex cursor-pointer list-none items-center justify-between px-4 py-3 text-sm font-semibold text-emerald-800">Sources & metadata <ChevronDown size={16} className={sourcesOpen ? 'rotate-180' : ''} /></summary><div className="space-y-2 border-t border-stone-200 p-3">{sources.map((source, index) => <SourceCard key={`${source.source}-${source.page}-${index}`} source={source} index={index} highlighted={highlighted === index + 1} />)}<p className="px-1 text-xs text-stone-500">{activeVersion.runtime} · {activeVersion.latencyMs.toLocaleString()} ms · {activeVersion.mode}</p></div></details>}<FeedbackModal open={feedbackOpen} onOpenChange={setFeedbackOpen} onSubmit={(reason, comment) => onFeedback(message.id, activeVersion.id, 'down', reason, comment)} /></>}
    </div>
  </article>
}
