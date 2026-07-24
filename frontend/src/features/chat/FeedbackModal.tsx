import { useState } from 'react'
import * as Dialog from '@radix-ui/react-dialog'
import { X } from 'lucide-react'

const reasons = ['Incorrect answer', 'Missing evidence', 'Citation problem', 'Not relevant', 'Unsafe or unclear']

export function FeedbackModal({ open, onOpenChange, onSubmit }: { open: boolean; onOpenChange: (open: boolean) => void; onSubmit: (reason: string, comment: string) => Promise<void> }) {
  const [reason, setReason] = useState('')
  const [comment, setComment] = useState('')
  const [saving, setSaving] = useState(false)
  async function submit() {
    if (!reason) return
    setSaving(true)
    try { await onSubmit(reason, comment); setReason(''); setComment(''); onOpenChange(false) } finally { setSaving(false) }
  }
  return <Dialog.Root open={open} onOpenChange={onOpenChange}><Dialog.Portal><Dialog.Overlay className="fixed inset-0 z-40 bg-stone-950/45 backdrop-blur-sm" /><Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,520px)] -translate-x-1/2 -translate-y-1/2 rounded-3xl bg-white p-6 shadow-2xl"><div className="flex items-start justify-between"><div><Dialog.Title className="text-xl font-bold">Help us improve this answer</Dialog.Title><Dialog.Description className="mt-1 text-sm text-stone-600">Choose one reason. A comment is optional.</Dialog.Description></div><Dialog.Close className="rounded-lg p-2 hover:bg-stone-100" aria-label="Close feedback"><X size={18} /></Dialog.Close></div><div className="mt-5 flex flex-wrap gap-2">{reasons.map((item) => <button type="button" key={item} onClick={() => setReason(item)} className={`rounded-full border px-3 py-2 text-sm ${reason === item ? 'border-emerald-700 bg-emerald-700 text-white' : 'border-stone-300 hover:border-emerald-400'}`}>{item}</button>)}</div><label className="mt-5 block text-sm font-semibold" htmlFor="feedback-comment">Additional comment</label><textarea id="feedback-comment" value={comment} onChange={(event) => setComment(event.target.value)} maxLength={1000} className="mt-2 min-h-28 w-full rounded-xl border border-stone-300 p-3 outline-none focus:ring-2 focus:ring-emerald-500" placeholder="Tell us what should be improved…" /><button type="button" disabled={!reason || saving} onClick={() => void submit()} className="mt-5 w-full rounded-xl bg-emerald-700 px-4 py-3 font-semibold text-white disabled:opacity-50">{saving ? 'Saving feedback…' : 'Submit feedback'}</button></Dialog.Content></Dialog.Portal></Dialog.Root>
}
