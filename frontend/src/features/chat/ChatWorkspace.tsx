import { type FormEvent, useEffect, useState } from 'react'
import { ArrowUp, CheckCircle2, LoaderCircle, ShieldCheck, ThumbsDown, ThumbsUp } from 'lucide-react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { Button } from '../../components/ui/Button'
import { sentinelApi } from '../../services/api'
import type { RagAnswer, SystemStatus } from '../../types/rag'
import { SourceCard } from './SourceCard'

const suggestions = ['What is CIS Control 1?', 'How should accounts be managed?', 'Explain Implementation Groups']

export function ChatWorkspace() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<RagAnswer | null>(null)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { sentinelApi.status().then(setStatus).catch(() => setError('Backend unavailable. Start the FastAPI server.')) }, [])

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const value = question.trim()
    if (!value || loading) return
    setLoading(true); setAnswer(null); setError('')
    try { setAnswer(await sentinelApi.ask(value)) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Unable to fetch an answer.') }
    finally { setLoading(false) }
  }

  return <Tooltip.Provider><main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#ecfccb_0,transparent_30%),linear-gradient(135deg,#fafaf9,#f5f5f4)] text-stone-900">
    <div className="mx-auto grid min-h-screen max-w-[1600px] lg:grid-cols-[280px_1fr]">
      <aside className="flex flex-col bg-[#0d3028] p-7 text-white">
        <div className="flex items-center gap-3"><div className="grid size-12 place-items-center rounded-2xl border border-emerald-300/30 text-xl font-bold text-lime-300">S</div><div><h1 className="text-2xl font-bold">Sentinel</h1><p className="text-xs tracking-[.18em] text-emerald-200">CIS INTELLIGENCE</p></div></div>
        <nav className="mt-16 space-y-3 text-sm"><div className="rounded-xl bg-white/10 px-4 py-3 font-semibold">Ask Sentinel</div><div className="px-4 py-3 text-emerald-100">Knowledge base</div><div className="px-4 py-3 text-emerald-100">Evaluation</div></nav>
        <Tooltip.Root><Tooltip.Trigger asChild><div className="mt-auto rounded-2xl border border-emerald-300/20 bg-white/5 p-4"><p className="flex items-center gap-2 font-semibold"><ShieldCheck size={18} className="text-lime-300" /> Private by design</p><p className="mt-2 text-sm leading-6 text-emerald-100">Models and documents stay on this machine.</p></div></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="rounded-lg bg-stone-900 px-3 py-2 text-xs text-white" side="right">No cloud model API required.</Tooltip.Content></Tooltip.Portal></Tooltip.Root>
      </aside>
      <section className="px-5 py-10 sm:px-10 lg:px-16">
        <header className="mx-auto max-w-4xl text-center"><div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-semibold text-emerald-800"><CheckCircle2 size={14} /> {status ? `Index ready · ${status.runtime}` : 'Connecting to index'}</div><h2 className="text-3xl font-bold tracking-tight sm:text-5xl">Ask the controls. <span className="text-emerald-700">Get grounded answers.</span></h2><p className="mt-4 text-stone-600">Explore CIS Controls v8 with answers traced directly to the source.</p></header>
        <form onSubmit={submit} className="mx-auto mt-10 max-w-4xl rounded-3xl border border-stone-200 bg-white p-5 shadow-xl shadow-stone-900/5"><textarea value={question} onChange={(event) => setQuestion(event.target.value)} placeholder="What would you like to understand?" className="min-h-28 w-full resize-none bg-transparent text-lg outline-none placeholder:text-stone-400" /><div className="flex items-center justify-between"><span className="text-xs text-stone-400">Enter to ask · Shift + Enter for new line</span><Button disabled={loading} aria-label="Ask Sentinel">{loading ? <LoaderCircle className="animate-spin" /> : <ArrowUp />}</Button></div></form>
        <div className="mx-auto mt-4 flex max-w-4xl flex-wrap justify-center gap-2">{suggestions.map((item) => <button key={item} onClick={() => setQuestion(item)} className="rounded-full border border-stone-200 bg-white/70 px-4 py-2 text-sm text-stone-600 hover:border-emerald-300">{item}</button>)}</div>
        {error && <div className="mx-auto mt-8 max-w-4xl rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}
        {answer && <section className="mx-auto mt-10 max-w-5xl rounded-3xl border border-stone-200 bg-white p-6 shadow-xl shadow-stone-900/5 sm:p-8"><div className="flex items-center justify-between"><p className="text-xs font-bold tracking-[.18em] text-emerald-700">GROUNDED RESPONSE</p><span className="rounded-full bg-stone-100 px-3 py-1 text-xs text-stone-600">{answer.mode}</span></div><p className="mt-6 text-lg leading-8 text-stone-800">{answer.answer}</p><div className="mt-6 grid gap-3">{answer.sources.map((source, index) => <SourceCard key={`${source.page}-${index}`} source={source} index={index} />)}</div><footer className="mt-6 flex items-center justify-between border-t border-stone-100 pt-5 text-sm text-stone-500"><span>{answer.latency_ms.toLocaleString()} ms · {answer.runtime}</span><div className="flex gap-2"><button onClick={() => sentinelApi.feedback(question, answer.answer, 'up')} aria-label="Useful" className="rounded-lg p-2 hover:bg-stone-100"><ThumbsUp size={18} /></button><button onClick={() => sentinelApi.feedback(question, answer.answer, 'down')} aria-label="Not useful" className="rounded-lg p-2 hover:bg-stone-100"><ThumbsDown size={18} /></button></div></footer></section>}
      </section>
    </div>
  </main></Tooltip.Provider>
}
