import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from 'react'
import { ArrowUp, CheckCircle2, LoaderCircle, ShieldCheck } from 'lucide-react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { Button } from '../../components/ui/Button'
import { sentinelApi } from '../../services/api'
import type { ChatMessage, StreamMeta, StreamPhase, SystemStatus } from '../../types/rag'
import { MessageBubble } from './MessageBubble'

const welcome: ChatMessage = { id: 'welcome', role: 'assistant', label: 'SENTINEL', content: 'Ask me about **CIS Controls v8**. I will retrieve local evidence and stream a grounded answer.' }
const suggestions = ['What is CIS Control 1?', 'How should accounts be managed?', 'Explain Implementation Groups']

export function ChatWorkspace() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([welcome])
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [phase, setPhase] = useState<StreamPhase>('idle')
  const [phaseMessage, setPhaseMessage] = useState('')
  const [meta, setMeta] = useState<StreamMeta | null>(null)
  const [error, setError] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const loading = phase === 'retrieving' || phase === 'generating'

  useEffect(() => { sentinelApi.status().then(setStatus).catch(() => setError('Backend unavailable. Start the FastAPI server.')) }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, phaseMessage])

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const value = question.trim()
    if (!value || loading) return
    const assistantId = `assistant-${Date.now()}`
    setMessages((current) => [...current, { id: `user-${Date.now()}`, role: 'user', content: value }, { id: assistantId, role: 'assistant', label: 'STREAMING', content: '' }])
    setQuestion(''); setError(''); setMeta(null); setPhase('retrieving'); setPhaseMessage('Connecting to the retrieval pipeline…')
    try {
      await sentinelApi.streamAsk(value, {
        onStatus: (next, message) => { setPhase(next as StreamPhase); setPhaseMessage(message) },
        onToken: (token) => setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + token } : message)),
        onDone: (result) => { setMeta(result); setPhase('complete'); setPhaseMessage(''); setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, label: result.mode.toUpperCase() } : message)) },
      })
    } catch (cause) { setPhase('error'); setPhaseMessage(''); setError(cause instanceof Error ? cause.message : 'Streaming failed.') }
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit() } }

  return <Tooltip.Provider><main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#ecfccb_0,transparent_30%),linear-gradient(135deg,#fafaf9,#f5f5f4)] text-stone-900"><div className="mx-auto grid min-h-screen max-w-[1600px] lg:grid-cols-[280px_1fr]">
    <aside className="flex flex-col bg-[#0d3028] p-7 text-white"><div className="flex items-center gap-3"><div className="grid size-12 place-items-center rounded-2xl border border-emerald-300/30 text-xl font-bold text-lime-300">S</div><div><h1 className="text-2xl font-bold">Sentinel</h1><p className="text-xs tracking-[.18em] text-emerald-200">CIS INTELLIGENCE</p></div></div><nav className="mt-16 space-y-3 text-sm"><div className="rounded-xl bg-white/10 px-4 py-3 font-semibold">Ask Sentinel</div><div className="px-4 py-3 text-emerald-100">Knowledge base</div><div className="px-4 py-3 text-emerald-100">Evaluation</div></nav><Tooltip.Root><Tooltip.Trigger asChild><div className="mt-auto rounded-2xl border border-emerald-300/20 bg-white/5 p-4"><p className="flex items-center gap-2 font-semibold"><ShieldCheck size={18} className="text-lime-300" /> Private by design</p><p className="mt-2 text-sm leading-6 text-emerald-100">Models and documents stay on this machine.</p></div></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="rounded-lg bg-stone-900 px-3 py-2 text-xs text-white" side="right">No cloud model API required.</Tooltip.Content></Tooltip.Portal></Tooltip.Root></aside>
    <section className="flex min-h-screen flex-col px-5 py-8 sm:px-10 lg:px-16"><header className="mx-auto w-full max-w-5xl border-b border-stone-200 pb-6"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-3xl font-bold tracking-tight">Security knowledge workspace</h2><p className="mt-2 text-stone-600">Streaming grounded answers from the local RAG pipeline.</p></div><div className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold ${status ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-800'}`}><CheckCircle2 size={14} />{status ? `Backend connected · ${status.runtime}` : 'Checking backend'}</div></div></header>
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col"><div className="flex-1 space-y-5 py-8" aria-live="polite">{messages.map((message) => <MessageBubble key={message.id} message={message} />)}{loading && <div className="flex items-center gap-3 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><LoaderCircle size={18} className="animate-spin" /><span>{phaseMessage}</span><span className="animate-pulse">•••</span></div>}{error && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}{meta && <p className="text-right text-xs text-stone-400">{meta.latency_ms.toLocaleString()} ms · {meta.runtime}</p>}<div ref={bottomRef} /></div>
        <div className="sticky bottom-0 bg-gradient-to-t from-stone-100 via-stone-100 to-transparent pb-4 pt-8"><div className="mb-3 flex flex-wrap gap-2">{suggestions.map((item) => <button key={item} onClick={() => setQuestion(item)} className="rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs text-stone-600 hover:border-emerald-300">{item}</button>)}</div><form onSubmit={submit} className="rounded-3xl border border-stone-200 bg-white p-4 shadow-xl shadow-stone-900/5"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleKeyDown} disabled={loading} placeholder="Ask a CIS Controls question…" className="min-h-20 w-full resize-none bg-transparent outline-none placeholder:text-stone-400 disabled:opacity-60" /><div className="flex items-center justify-between"><span className="text-xs text-stone-400">Enter to send · Shift + Enter for new line</span><Button disabled={loading} aria-label="Send question">{loading ? <LoaderCircle className="animate-spin" /> : <ArrowUp />}</Button></div></form></div>
      </div>
    </section>
  </div></main></Tooltip.Provider>
}
