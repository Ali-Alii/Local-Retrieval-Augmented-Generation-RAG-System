import { Bot, User } from 'lucide-react'

export type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  label?: string
}

export function MessageBubble({ message }: { message: ChatMessage }) {
  const assistant = message.role === 'assistant'
  return <article className={`flex gap-3 ${assistant ? '' : 'flex-row-reverse'}`}>
    <div className={`grid size-9 shrink-0 place-items-center rounded-xl ${assistant ? 'bg-emerald-800 text-white' : 'bg-stone-200 text-stone-700'}`}>
      {assistant ? <Bot size={18} /> : <User size={18} />}
    </div>
    <div className={`max-w-[82%] rounded-2xl px-5 py-4 ${assistant ? 'border border-stone-200 bg-white' : 'bg-emerald-700 text-white'}`}>
      {message.label && <p className={`mb-2 text-[11px] font-bold tracking-[.16em] ${assistant ? 'text-emerald-700' : 'text-emerald-100'}`}>{message.label}</p>}
      <p className="whitespace-pre-wrap leading-7">{message.content}</p>
    </div>
  </article>
}
