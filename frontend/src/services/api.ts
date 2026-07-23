import type { StreamMeta, SystemStatus, UserProfile } from '../types/rag'

const MIDDLEWARE_URL = import.meta.env.VITE_MIDDLEWARE_URL ?? 'http://127.0.0.1:5100'
const RAG_URL = `${MIDDLEWARE_URL}/api/rag`
type Handlers = { onStatus: (phase: string, message: string) => void; onToken: (token: string) => void; onDone: (meta: StreamMeta) => void }

async function errorFrom(response: Response): Promise<Error> {
  const body = await response.json().catch(() => ({}))
  return new Error(body.detail ?? body.title ?? body.message ?? `Request failed (${response.status})`)
}

async function refreshSession(): Promise<boolean> {
  const response = await fetch(`${MIDDLEWARE_URL}/api/auth/refresh`, { method: 'POST', credentials: 'include' })
  return response.ok
}

async function authenticatedFetch(url: string, init?: RequestInit): Promise<Response> {
  const send = () => fetch(url, { ...init, credentials: 'include', headers: { 'Content-Type': 'application/json', ...init?.headers } })
  let response = await send()
  if (response.status === 401 && await refreshSession()) response = await send()
  return response
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await authenticatedFetch(url, init)
  if (!response.ok) throw await errorFrom(response)
  return response.json() as Promise<T>
}

async function streamAsk(question: string, handlers: Handlers): Promise<void> {
  const response = await authenticatedFetch(`${RAG_URL}/query/stream`, { method: 'POST', headers: { Accept: 'text/event-stream' }, body: JSON.stringify({ question }) })
  if (!response.ok || !response.body) throw await errorFrom(response)
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

export const sentinelApi = { status: () => request<SystemStatus>(`${RAG_URL}/status`), streamAsk }
export const authApi = {
  me: () => request<UserProfile>(`${MIDDLEWARE_URL}/api/auth/me`),
  developmentLogin: () => request<UserProfile>(`${MIDDLEWARE_URL}/api/auth/development`, { method: 'POST' }),
  logout: () => request<{ ok: boolean }>(`${MIDDLEWARE_URL}/api/auth/logout`, { method: 'POST' }),
  googleLoginUrl: `${MIDDLEWARE_URL}/api/auth/login/google`,
}
