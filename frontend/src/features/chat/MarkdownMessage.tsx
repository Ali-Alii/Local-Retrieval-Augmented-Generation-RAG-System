import { Children, type ReactNode } from 'react'
import * as Tooltip from '@radix-ui/react-tooltip'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { Source } from '../../types/rag'

function CitationText({ text, sources, onCitation }: { text: string; sources: Source[]; onCitation: (index: number) => void }) {
  return text.split(/(\[\d+\])/g).map((part, position) => {
    const match = part.match(/^\[(\d+)\]$/)
    if (!match) return part
    const index = Number(match[1])
    const source = sources[index - 1]
    if (!source) return part
    return <Tooltip.Root key={`${part}-${position}`}><Tooltip.Trigger asChild><button type="button" onClick={() => onCitation(index)} className="mx-0.5 inline-flex rounded-md bg-emerald-100 px-1.5 py-0.5 text-xs font-bold text-emerald-800 ring-1 ring-emerald-300 hover:bg-emerald-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600">[{index}]</button></Tooltip.Trigger><Tooltip.Portal><Tooltip.Content side="top" className="z-50 max-w-sm rounded-xl bg-stone-950 p-3 text-xs leading-5 text-white shadow-xl"><strong>{source.source} · page {source.page}</strong><p className="mt-1 text-stone-200">{source.text.slice(0, 260)}</p><Tooltip.Arrow className="fill-stone-950" /></Tooltip.Content></Tooltip.Portal></Tooltip.Root>
  })
}

function renderInline(children: ReactNode, sources: Source[], onCitation: (index: number) => void): ReactNode {
  return Children.map(children, (child) => typeof child === 'string' ? <CitationText text={child} sources={sources} onCitation={onCitation} /> : child)
}

export function MarkdownMessage({ content, sources = [], onCitation }: { content: string; sources?: Source[]; onCitation: (index: number) => void }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    p: ({ children }) => <p className="my-2 leading-7 first:mt-0 last:mb-0">{renderInline(children, sources, onCitation)}</p>,
    li: ({ children }) => <li>{renderInline(children, sources, onCitation)}</li>,
    strong: ({ children }) => <strong className="font-bold text-inherit">{renderInline(children, sources, onCitation)}</strong>,
    ul: ({ children }) => <ul className="my-3 list-disc space-y-1 pl-6">{children}</ul>,
    ol: ({ children }) => <ol className="my-3 list-decimal space-y-1 pl-6">{children}</ol>,
    code: ({ className, children, ...props }) => className
      ? <code className={`${className} my-3 block overflow-x-auto rounded-xl bg-stone-950 p-4 text-sm text-stone-100`} {...props}>{children}</code>
      : <code className="rounded bg-stone-200/70 px-1.5 py-0.5 text-sm" {...props}>{children}</code>,
  }}>{content}</ReactMarkdown>
}
