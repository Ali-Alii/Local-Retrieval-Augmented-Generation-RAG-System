import type { RagAnswer, SystemStatus } from '../types/rag'

const API_URL = import.meta.env.VITE_API_URL ?? 'http://127.0.0.1:8000/api/v1'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail ?? `Request failed (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const sentinelApi = {
  status: () => request<SystemStatus>('/status'),
  ask: (question: string) => request<RagAnswer>('/ask', { method: 'POST', body: JSON.stringify({ question }) }),
  feedback: (question: string, answer: string, rating: 'up' | 'down') => request<{ ok: boolean }>('/feedback', {
    method: 'POST', body: JSON.stringify({ question, answer, rating }),
  }),
}
