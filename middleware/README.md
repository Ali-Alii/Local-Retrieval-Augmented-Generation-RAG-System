# Sentinel RAG Middleware

The middleware is the security boundary between React and the Python RAG API.

```text
React (5173) -> .NET middleware (5100) -> Python FastAPI RAG (8000)
                         |
                         +-> MongoDB (27017): users, sessions, conversations, feedback, audit logs
```

## Responsibilities

- Google OAuth login and development-only local login
- Short-lived JWT access sessions in `HttpOnly` cookies
- Rotating refresh tokens stored as SHA-256 hashes
- Protected proxy endpoints with SSE passthrough
- Python RAG credentials attached only by `RagApiClient`
- MongoDB user, session, conversation, response-version, feedback, and audit persistence
- Request audit middleware, rate limiting, safe errors, CORS, and Swagger

## Local configuration

Never put secret values in committed `appsettings.json` files.

```powershell
dotnet user-secrets set "Jwt:SigningKey" "<at-least-32-random-characters>" --project middleware/src/RagMiddleware.Api
dotnet user-secrets set "Mongo:ConnectionString" "mongodb://127.0.0.1:27017" --project middleware/src/RagMiddleware.Api
dotnet user-secrets set "Authentication:Google:ClientId" "<google-client-id>" --project middleware/src/RagMiddleware.Api
dotnet user-secrets set "Authentication:Google:ClientSecret" "<google-client-secret>" --project middleware/src/RagMiddleware.Api
```

The approved Google redirect URI is:

```text
http://127.0.0.1:5100/signin-google
```

For local testing without Google credentials, enable the development endpoint only in the Development environment:

```powershell
dotnet user-secrets set "Authentication:EnableDevelopmentLogin" "true" --project middleware/src/RagMiddleware.Api
```

## Run

```powershell
docker compose up -d mongodb weaviate
$env:RAG_RUNTIME="exact"
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
dotnet run --project middleware/src/RagMiddleware.Api --urls http://127.0.0.1:5100
cd frontend
npm run dev
```

Swagger: `http://127.0.0.1:5100/swagger`

## Credential inventory

| Secret | Purpose | Storage |
|---|---|---|
| `Jwt:SigningKey` | Signs middleware session tokens | User Secrets / Key Vault |
| `Authentication:Google:ClientId` | Identifies OAuth application | User Secrets / Key Vault |
| `Authentication:Google:ClientSecret` | Authenticates OAuth application | User Secrets / Key Vault |
| `RagApi:ApiKey` | Optional Python API credential; currently unused locally | User Secrets / Key Vault |
| `Mongo:ConnectionString` | MongoDB credentials/endpoint | User Secrets / environment |

No value from this table is returned to React, serialized into API responses, or written to audit logs.

## API

- `GET /health` - public health check
- `GET /api/auth/login/google` - Google login
- `POST /api/auth/development` - local Development-only login
- `GET /api/auth/me`, `POST /api/auth/refresh`, `POST /api/auth/logout`
- `GET /api/rag/status`
- `POST /api/rag/query`
- `POST /api/rag/query/stream` - SSE passthrough plus conversation/version persistence
- `GET /api/rag/evaluation`, `POST /api/rag/feedback`
- `GET|POST /api/conversations` - list and create chat threads
- `GET /api/conversations/{id}` - restore a complete thread
- `PUT /api/conversations/{id}/messages/{messageId}/active-version` - select a response version
- `POST /api/feedback` - persist thumbs up/down, reason, and optional comment
- `GET /api/admin/audit-logs` - `Admin` role only

## Production plan

Use HTTPS, Azure Key Vault or deployment environment variables, authenticated MongoDB, an explicit CORS origin, and real Google credentials. Disable development login. Access tokens remain in secure `HttpOnly` cookies and refresh tokens are rotated after every use.
