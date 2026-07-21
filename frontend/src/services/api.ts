import type { StreamMeta, SystemStatus } from '../types/rag'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1'
type Handlers = { onStatus: (phase: string, message: string) => void; onToken: (token: string) => void; onDone: (meta: StreamMeta) => void }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, { ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } })
  if (!response.ok) { const body = await response.json().catch(() => ({})); throw new Error(body.detail ?? `Request failed (${response.status})`) }
  return response.json() as Promise<T>
}

async function streamAsk(question: string, handlers: Handlers): Promise<void> {
  const response = await fetch(`${API_URL}/ask/stream`, { method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' }, body: JSON.stringify({ question }) })
  if (!response.ok || !response.body) throw new Error(`Streaming request failed (${response.status})`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { value, done } = await reader.read()
    buffer += decoder.decode(value, { stream: !done })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() ?? ''
    for (const block of blocks) {
      const event = block.match(/^event: (.+)$/m)?.[1]
      const raw = block.match(/^data: (.+)$/m)?.[1]
      if (!event || !raw) continue
      const data = JSON.parse(raw)
      if (event === 'status') handlers.onStatus(data.phase, data.message)
      else if (event === 'token') handlers.onToken(data.content)
      else if (event === 'done') handlers.onDone(data)
      else if (event === 'error') throw new Error(data.message)
    }
    if (done) break
  }
}

export const sentinelApi = { status: () => request<SystemStatus>('/status'), streamAsk }
