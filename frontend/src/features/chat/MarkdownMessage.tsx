import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export function MarkdownMessage({ content }: { content: string }) {
  return <ReactMarkdown remarkPlugins={[remarkGfm]} components={{
    p: ({ children }) => <p className="my-2 leading-7 first:mt-0 last:mb-0">{children}</p>,
    strong: ({ children }) => <strong className="font-bold text-inherit">{children}</strong>,
    ul: ({ children }) => <ul className="my-3 list-disc space-y-1 pl-6">{children}</ul>,
    ol: ({ children }) => <ol className="my-3 list-decimal space-y-1 pl-6">{children}</ol>,
    code: ({ className, children, ...props }) => className
      ? <code className={`${className} my-3 block overflow-x-auto rounded-xl bg-stone-950 p-4 text-sm text-stone-100`} {...props}>{children}</code>
      : <code className="rounded bg-stone-200/70 px-1.5 py-0.5 text-sm" {...props}>{children}</code>,
  }}>{content}</ReactMarkdown>
}
