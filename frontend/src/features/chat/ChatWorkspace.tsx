import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from 'react'
import { ArrowUp, CheckCircle2, LoaderCircle, ShieldCheck } from 'lucide-react'
import * as Tooltip from '@radix-ui/react-tooltip'
import { Button } from '../../components/ui/Button'
import { authApi, conversationsApi, feedbackApi, sentinelApi } from '../../services/api'
import type { ChatMessage, ConversationSummary, FeedbackPayload, StreamMeta, StreamPhase, SystemStatus, UserProfile } from '../../types/rag'
import { GuidedTour } from './GuidedTour'
import { MessageBubble } from './MessageBubble'
import { ThreadList } from './ThreadList'

const welcome: ChatMessage = { id: 'welcome', role: 'assistant', label: 'SENTINEL', content: 'Ask me about **CIS Controls v8**. I will retrieve local evidence and stream a grounded answer.' }
const suggestions = ['What is CIS Control 1?', 'How should accounts be managed?', 'Explain Implementation Groups']

export function ChatWorkspace() {
  const [question, setQuestion] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([welcome])
  const [threads, setThreads] = useState<ConversationSummary[]>([])
  const [activeConversationId, setActiveConversationId] = useState<string | null>(null)
  const [status, setStatus] = useState<SystemStatus | null>(null)
  const [phase, setPhase] = useState<StreamPhase>('idle')
  const [phaseMessage, setPhaseMessage] = useState('')
  const [meta, setMeta] = useState<StreamMeta | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [user, setUser] = useState<UserProfile | null>(null)
  const bottomRef = useRef<HTMLDivElement>(null)
  const tokenQueueRef = useRef('')
  const revealTimerRef = useRef<number | null>(null)
  const pendingDoneRef = useRef<StreamMeta | null>(null)
  const reloadConversationRef = useRef<string | null>(null)
  const loading = phase === 'retrieving' || phase === 'generating'

  async function refreshThreads() {
    const list = await conversationsApi.list()
    setThreads(list)
    return list
  }

  async function openConversation(id: string) {
    const conversation = await conversationsApi.get(id)
    setActiveConversationId(id)
    setMessages(conversation.messages.length ? conversation.messages : [welcome])
    setMeta(null)
    setError('')
  }

  useEffect(() => {
    authApi.me().then(async (profile) => {
      setUser(profile)
      const [nextStatus, list] = await Promise.all([sentinelApi.status(), refreshThreads()])
      setStatus(nextStatus)
      if (list[0]) await openConversation(list[0].id)
    }).catch(() => setError('Sign in to access the protected RAG workspace.'))
  }, [])
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }) }, [messages, phaseMessage])
  useEffect(() => () => { if (revealTimerRef.current !== null) window.clearTimeout(revealTimerRef.current) }, [])

  function completeStream(assistantId: string, result: StreamMeta) {
    pendingDoneRef.current = null
    setMeta(result); setPhase('complete'); setPhaseMessage('')
    setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, label: result.mode.toUpperCase() } : message))
    const conversationId = reloadConversationRef.current
    reloadConversationRef.current = null
    if (conversationId) void Promise.all([openConversation(conversationId), refreshThreads()])
  }

  function startPacedReveal(assistantId: string) {
    if (revealTimerRef.current !== null) return
    const reveal = () => {
      if (!tokenQueueRef.current) {
        revealTimerRef.current = null
        if (pendingDoneRef.current) completeStream(assistantId, pendingDoneRef.current)
        return
      }
      const visible = tokenQueueRef.current.slice(0, 2)
      tokenQueueRef.current = tokenQueueRef.current.slice(visible.length)
      setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: message.content + visible } : message))
      revealTimerRef.current = window.setTimeout(reveal, 24)
    }
    revealTimerRef.current = window.setTimeout(reveal, 24)
  }

  async function runStream(value: string, conversationId: string, assistantMessageId?: string) {
    const assistantId = assistantMessageId ?? `assistant-${Date.now()}`
    tokenQueueRef.current = ''; pendingDoneRef.current = null; reloadConversationRef.current = null
    if (revealTimerRef.current !== null) window.clearTimeout(revealTimerRef.current)
    revealTimerRef.current = null
    if (assistantMessageId) setMessages((current) => current.map((message) => message.id === assistantId ? { ...message, content: '', versions: undefined, activeVersionId: undefined, label: 'REGENERATING' } : message))
    else setMessages((current) => [...current, { id: `user-${Date.now()}`, role: 'user', content: value }, { id: assistantId, role: 'assistant', label: 'STREAMING', content: '' }])
    setError(''); setNotice(''); setMeta(null); setPhase('retrieving'); setPhaseMessage('Retrieving grounded evidence…')
    try {
      await sentinelApi.streamAsk(value, conversationId, {
        onStatus: (next, message) => { setPhase(next as StreamPhase); setPhaseMessage(message) },
        onSources: () => undefined,
        onToken: (token) => { tokenQueueRef.current += token; startPacedReveal(assistantId) },
        onPersisted: (result) => { reloadConversationRef.current = result.conversationId },
        onDone: (result) => {
          pendingDoneRef.current = result; setPhaseMessage('Saving the response…')
          if (!tokenQueueRef.current && revealTimerRef.current === null) completeStream(assistantId, result)
        },
      }, assistantMessageId)
    } catch (cause) {
      setPhase('error'); setPhaseMessage(''); setError(cause instanceof Error ? cause.message : 'Streaming failed.')
      await openConversation(conversationId).catch(() => undefined)
    }
  }

  async function submit(event?: FormEvent) {
    event?.preventDefault()
    const value = question.trim()
    if (!value || loading || !user) return
    setQuestion('')
    let conversationId = activeConversationId
    if (!conversationId) {
      const conversation = await conversationsApi.create(value.slice(0, 64))
      conversationId = conversation.id; setActiveConversationId(conversationId); await refreshThreads()
    }
    await runStream(value, conversationId)
  }

  async function regenerate(message: ChatMessage) {
    if (!activeConversationId || loading) return
    const index = messages.findIndex((item) => item.id === message.id)
    const prompt = [...messages.slice(0, index)].reverse().find((item) => item.role === 'user')?.content
    if (prompt) await runStream(prompt, activeConversationId, message.id)
  }

  async function changeVersion(messageId: string, versionId: string) {
    if (!activeConversationId) return
    await conversationsApi.setActiveVersion(activeConversationId, messageId, versionId)
    setMessages((current) => current.map((message) => message.id === messageId ? { ...message, activeVersionId: versionId } : message))
  }

  async function submitFeedback(messageId: string, versionId: string, rating: 'up' | 'down', reason?: string, comment?: string) {
    if (!activeConversationId) return
    try {
      const payload: FeedbackPayload = { conversationId: activeConversationId, messageId, versionId, rating, reason, comment }
      await feedbackApi.submit(payload)
      setError('')
      setNotice(rating === 'up' ? 'Thanks—your positive feedback was saved.' : 'Thanks—your feedback was saved for review.')
      window.setTimeout(() => setNotice(''), 3500)
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : 'Feedback could not be saved.'
      setError(message)
      throw cause
    }
  }

  function newConversation() { setActiveConversationId(null); setMessages([welcome]); setMeta(null); setError(''); setNotice('') }
  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); void submit() } }
  async function developmentLogin() { try { const profile = await authApi.developmentLogin(); setUser(profile); setStatus(await sentinelApi.status()); const list = await refreshThreads(); if (list[0]) await openConversation(list[0].id); setError('') } catch (cause) { setError(cause instanceof Error ? cause.message : 'Development login failed.') } }
  async function logout() { await authApi.logout(); setUser(null); setStatus(null); setThreads([]); newConversation(); setError('Sign in to access the protected RAG workspace.') }

  return <Tooltip.Provider><main className="min-h-screen bg-[radial-gradient(circle_at_top_right,#ecfccb_0,transparent_30%),linear-gradient(135deg,#fafaf9,#f5f5f4)] text-stone-900"><div className="mx-auto grid min-h-screen max-w-[1600px] lg:grid-cols-[280px_1fr]">
    <aside className="flex flex-col bg-[#0d3028] p-7 text-white"><div className="flex items-center gap-3"><div className="grid size-12 place-items-center rounded-2xl border border-emerald-300/30 text-xl font-bold text-lime-300">S</div><div><h1 className="text-2xl font-bold">Sentinel</h1><p className="text-xs tracking-[.18em] text-emerald-200">CIS INTELLIGENCE</p></div></div><ThreadList threads={threads} activeId={activeConversationId} onNew={newConversation} onSelect={(id) => void openConversation(id)} /><Tooltip.Root><Tooltip.Trigger asChild><div className="mt-auto rounded-2xl border border-emerald-300/20 bg-white/5 p-4"><p className="flex items-center gap-2 font-semibold"><ShieldCheck size={18} className="text-lime-300" /> Private by design</p><p className="mt-2 text-sm leading-6 text-emerald-100">Models and documents stay on this machine.</p></div></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content className="rounded-lg bg-stone-900 px-3 py-2 text-xs text-white" side="right">No cloud model API required.</Tooltip.Content></Tooltip.Portal></Tooltip.Root></aside>
    <section className="flex min-h-screen flex-col px-5 py-8 sm:px-10 lg:px-16"><header className="mx-auto w-full max-w-5xl border-b border-stone-200 pb-6"><div className="flex flex-wrap items-center justify-between gap-4"><div><h2 className="text-3xl font-bold tracking-tight">Security knowledge workspace</h2><p className="mt-2 text-stone-600">Persistent, grounded conversations through the secure .NET middleware.</p></div><div className="flex items-center gap-2"><div className={`inline-flex items-center gap-2 rounded-full border px-3 py-2 text-xs font-semibold ${status ? 'border-emerald-200 bg-emerald-50 text-emerald-800' : 'border-amber-200 bg-amber-50 text-amber-800'}`}><CheckCircle2 size={14} />{status ? `Middleware connected · ${status.runtime}` : 'Authentication required'}</div>{user ? <button onClick={() => void logout()} className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-xs font-semibold">Sign out</button> : <><button onClick={() => window.location.assign(authApi.googleLoginUrl)} className="rounded-xl bg-emerald-700 px-3 py-2 text-xs font-semibold text-white">Sign in with Google</button>{import.meta.env.VITE_ENABLE_DEV_LOGIN === 'true' && <button onClick={() => void developmentLogin()} className="rounded-xl border border-stone-300 bg-white px-3 py-2 text-xs font-semibold">Local demo login</button>}</>}</div></div></header>
      <div className="mx-auto flex w-full max-w-5xl flex-1 flex-col"><div className="flex-1 space-y-5 py-8" aria-live="polite">{messages.map((message) => <MessageBubble key={message.id} message={message} busy={loading} onRegenerate={(item) => void regenerate(item)} onVersionChange={(messageId, versionId) => void changeVersion(messageId, versionId)} onFeedback={submitFeedback} />)}{loading && <div className="flex items-center gap-3 rounded-2xl bg-emerald-50 px-4 py-3 text-sm text-emerald-800"><LoaderCircle size={18} className="animate-spin" /><span>{phaseMessage}</span><span className="animate-pulse">•••</span></div>}{error && <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">{error}</div>}{notice && <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">{notice}</div>}{meta && <p className="text-right text-xs text-stone-400">{meta.latency_ms.toLocaleString()} ms · {meta.runtime}</p>}<div ref={bottomRef} /></div>
        <div className="sticky bottom-0 bg-gradient-to-t from-stone-100 via-stone-100 to-transparent pb-4 pt-8"><div className="mb-3 flex flex-wrap gap-2">{suggestions.map((item) => <button key={item} onClick={() => setQuestion(item)} disabled={!user} className="rounded-full border border-stone-200 bg-white px-3 py-1.5 text-xs text-stone-600 hover:border-emerald-300 disabled:opacity-50">{item}</button>)}</div><form onSubmit={submit} className="rounded-3xl border border-stone-200 bg-white p-4 shadow-xl shadow-stone-900/5"><label htmlFor="rag-question" className="sr-only">Ask a CIS Controls question</label><textarea id="rag-question" value={question} onChange={(event) => setQuestion(event.target.value)} onKeyDown={handleKeyDown} disabled={loading || !user} maxLength={1000} placeholder={user ? 'Ask a CIS Controls question…' : 'Sign in to ask a question'} className="min-h-20 w-full resize-none bg-transparent outline-none placeholder:text-stone-400 focus-visible:ring-2 focus-visible:ring-emerald-500 disabled:opacity-60" /><div className="flex items-center justify-between"><span className="text-xs text-stone-400">Enter to send · Shift + Enter for new line</span><Button disabled={loading || !user} aria-label="Send question">{loading ? <LoaderCircle className="animate-spin" /> : <ArrowUp />}</Button></div></form></div>
      </div>
    </section>
  </div>{notice && <div role="status" className="fixed bottom-6 right-6 z-50 rounded-2xl bg-emerald-800 px-5 py-3 font-semibold text-white shadow-2xl">✓ {notice}</div>}{user && <GuidedTour />}</main></Tooltip.Provider>
}
