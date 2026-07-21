export type Source = { source: string; page: number; text: string; score: number }
export type RagAnswer = { answer: string; mode: string; runtime: string; latency_ms: number; sources: Source[] }
export type SystemStatus = { documents: number; chunks: number; vectors: number; runtime: string; reranker: string; pipeline: string }
