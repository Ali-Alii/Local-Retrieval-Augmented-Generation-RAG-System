# Middleware Runbook

## Python RAG API is down

1. Check `http://127.0.0.1:8000/api/v1/health`.
2. Confirm Weaviate and Ollama are running.
3. Restart FastAPI; do not expose its credentials to React as a workaround.
4. The middleware returns a generic upstream-service error while retaining details in server logs.

## Rotate a Python RAG credential

1. Create the replacement credential at the Python service.
2. Update `RagApi:ApiKey` in User Secrets, Key Vault, or the deployment environment.
3. Restart the middleware and verify a protected query.
4. Revoke the old credential.

## Revoke a compromised Google secret

1. Rotate the secret in Google Cloud Console.
2. Replace `Authentication:Google:ClientSecret` in the secret store.
3. Restart the middleware.
4. Revoke active refresh sessions in MongoDB if user sessions may be affected.

## Audit retention

Retain security audit logs for 90 days in development and define the production period with the security/legal owner. Apply a MongoDB TTL index only after that decision is approved.
