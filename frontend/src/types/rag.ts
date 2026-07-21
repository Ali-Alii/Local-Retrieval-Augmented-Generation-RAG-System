export type Source = { source: string; page: number; text: string; score: number }
export type RagAnswer = { answer: string; mode: string; runtime: string; latency_ms: number; sources: Source[] }
export type SystemStatus = { documents: number; chunks: number; vectors: number; runtime: string; reranker: string; pipeline: string }
export type StreamPhase = 'idle' | 'retrieving' | 'generating' | 'complete' | 'error'
export type StreamMeta = Pick<RagAnswer, 'mode' | 'runtime' | 'latency_ms'>
export type ChatMessage = { id: string; role: 'user' | 'assistant'; content: string; label?: string }
