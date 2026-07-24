# Sentinel React Frontend

React 19 + TypeScript + Vite + Tailwind chat client for Sentinel. The browser communicates only with the .NET middleware; it never calls the Python RAG API directly.

## Development

```powershell
Copy-Item .env.example .env.local
npm install
npm run dev
```

Open `http://127.0.0.1:5173`.

`VITE_MIDDLEWARE_URL` defaults to `http://127.0.0.1:5100`. Authentication uses secure `HttpOnly` cookies. `VITE_ENABLE_DEV_LOGIN=true` displays the local-login button for development; production should omit it.

## Flow

```text
ChatWorkspace -> services/api.ts -> .NET middleware -> Python RAG
                                      <- SSE stream <-
```

The client handles session refresh, SSE status/token/done/error events, Markdown rendering, loading state, paced token display, and auto-scroll.

## Validation

```powershell
npm run lint
npm run build
```
