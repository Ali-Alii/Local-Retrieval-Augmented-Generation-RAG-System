using System.Diagnostics;
using System.Security.Claims;
using RagMiddleware.Application;
using RagMiddleware.Domain;

namespace RagMiddleware.Api;

public sealed class AuditMiddleware(RequestDelegate next, ILogger<AuditMiddleware> logger)
{
    public async Task InvokeAsync(HttpContext context, IAuditLogService auditLogs)
    {
        var path = context.Request.Path.Value ?? string.Empty;
        if (!path.StartsWith("/api/rag", StringComparison.OrdinalIgnoreCase) && !path.StartsWith("/api/auth", StringComparison.OrdinalIgnoreCase))
        {
            await next(context);
            return;
        }

        var stopwatch = Stopwatch.StartNew();
        try { await next(context); }
        finally
        {
            stopwatch.Stop();
            try
            {
                await auditLogs.RecordAsync(new AuditLog
                {
                    UserId = context.User.FindFirstValue(ClaimTypes.NameIdentifier),
                    Action = ActionFor(context.Request.Method, path, context.Response.StatusCode),
                    Endpoint = path,
                    RequestSummary = $"{context.Request.Method} {path}",
                    StatusCode = context.Response.StatusCode,
                    IpAddress = context.Connection.RemoteIpAddress?.ToString(),
                    DurationMs = stopwatch.ElapsedMilliseconds
                }, context.RequestAborted);
            }
            catch (Exception error) { logger.LogError(error, "Unable to persist audit log for {Path}", path); }
        }
    }

    private static string ActionFor(string method, string path, int status) => path switch
    {
        var value when value.Contains("login", StringComparison.OrdinalIgnoreCase) || value.Contains("google/callback", StringComparison.OrdinalIgnoreCase) || value.Contains("auth/development", StringComparison.OrdinalIgnoreCase) => status < 400 ? "LOGIN_SUCCESS" : "LOGIN_FAILED",
        var value when value.Contains("logout", StringComparison.OrdinalIgnoreCase) => "LOGOUT",
        var value when value.Contains("query", StringComparison.OrdinalIgnoreCase) => "RAG_QUERY",
        _ => $"{method}_{path.Trim('/').Replace('/', '_').ToUpperInvariant()}"
    };
}
