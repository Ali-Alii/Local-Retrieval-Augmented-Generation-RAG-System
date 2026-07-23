using System.Text.Json;
using RagMiddleware.Domain;

namespace RagMiddleware.Application;

public interface IUserRepository
{
    Task<User?> GetByIdAsync(string id, CancellationToken cancellationToken);
    Task<User> UpsertGoogleUserAsync(GoogleProfile profile, CancellationToken cancellationToken);
}

public interface IRefreshSessionRepository
{
    Task CreateAsync(RefreshSession session, CancellationToken cancellationToken);
    Task<RefreshSession?> GetActiveByHashAsync(string tokenHash, CancellationToken cancellationToken);
    Task RevokeAsync(string tokenHash, CancellationToken cancellationToken);
    Task RevokeAllForUserAsync(string userId, CancellationToken cancellationToken);
}

public interface IAuditLogRepository
{
    Task WriteAsync(AuditLog entry, CancellationToken cancellationToken);
    Task<PagedResult<AuditLog>> SearchAsync(int page, int pageSize, string? userId, string? action, DateTime? fromUtc, DateTime? toUtc, CancellationToken cancellationToken);
}

public interface IAuditLogService
{
    Task RecordAsync(AuditLog entry, CancellationToken cancellationToken);
}

public interface IRagApiClient
{
    Task<JsonDocument> GetStatusAsync(CancellationToken cancellationToken);
    Task<JsonDocument> QueryAsync(string question, CancellationToken cancellationToken);
    Task<HttpResponseMessage> StreamQueryAsync(string question, CancellationToken cancellationToken);
    Task<JsonDocument> GetEvaluationAsync(CancellationToken cancellationToken);
    Task SendFeedbackAsync(JsonElement payload, CancellationToken cancellationToken);
}

public interface ITokenService
{
    Task<SessionTokens> IssueAsync(User user, CancellationToken cancellationToken);
    Task<SessionTokens?> RefreshAsync(string refreshToken, CancellationToken cancellationToken);
    Task RevokeAsync(string refreshToken, CancellationToken cancellationToken);
}

public sealed record GoogleProfile(string Subject, string Email, string DisplayName, string? AvatarUrl);
public sealed record SessionTokens(string AccessToken, DateTime AccessExpiresAtUtc, string RefreshToken, DateTime RefreshExpiresAtUtc);
public sealed record UserProfile(string Id, string Email, string DisplayName, string? AvatarUrl, IReadOnlyCollection<string> Roles);
public sealed record PagedResult<T>(IReadOnlyCollection<T> Items, long Total, int Page, int PageSize);
