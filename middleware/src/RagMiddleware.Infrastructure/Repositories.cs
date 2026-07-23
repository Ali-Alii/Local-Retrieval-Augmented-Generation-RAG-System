using MongoDB.Driver;
using RagMiddleware.Application;
using RagMiddleware.Domain;

namespace RagMiddleware.Infrastructure;

public sealed class UserRepository(MongoStore store) : IUserRepository
{
    public Task<User?> GetByIdAsync(string id, CancellationToken cancellationToken) =>
        store.Users.Find(x => x.Id == id).FirstOrDefaultAsync(cancellationToken)!;

    public async Task<User> UpsertGoogleUserAsync(GoogleProfile profile, CancellationToken cancellationToken)
    {
        var existing = await store.Users.Find(x => x.GoogleSubject == profile.Subject).FirstOrDefaultAsync(cancellationToken);
        if (existing is null)
        {
            existing = new User { GoogleSubject = profile.Subject, Email = profile.Email, DisplayName = profile.DisplayName, AvatarUrl = profile.AvatarUrl };
            await store.Users.InsertOneAsync(existing, cancellationToken: cancellationToken);
            return existing;
        }
        existing.Email = profile.Email;
        existing.DisplayName = profile.DisplayName;
        existing.AvatarUrl = profile.AvatarUrl;
        existing.LastLoginAtUtc = DateTime.UtcNow;
        await store.Users.ReplaceOneAsync(x => x.Id == existing.Id, existing, cancellationToken: cancellationToken);
        return existing;
    }
}

public sealed class RefreshSessionRepository(MongoStore store) : IRefreshSessionRepository
{
    public Task CreateAsync(RefreshSession session, CancellationToken cancellationToken) => store.RefreshSessions.InsertOneAsync(session, cancellationToken: cancellationToken);
    public Task<RefreshSession?> GetActiveByHashAsync(string tokenHash, CancellationToken cancellationToken) =>
        store.RefreshSessions.Find(x => x.TokenHash == tokenHash && x.RevokedAtUtc == null && x.ExpiresAtUtc > DateTime.UtcNow).FirstOrDefaultAsync(cancellationToken)!;
    public Task RevokeAsync(string tokenHash, CancellationToken cancellationToken) =>
        store.RefreshSessions.UpdateOneAsync(x => x.TokenHash == tokenHash, Builders<RefreshSession>.Update.Set(x => x.RevokedAtUtc, DateTime.UtcNow), cancellationToken: cancellationToken);
    public Task RevokeAllForUserAsync(string userId, CancellationToken cancellationToken) =>
        store.RefreshSessions.UpdateManyAsync(x => x.UserId == userId && x.RevokedAtUtc == null, Builders<RefreshSession>.Update.Set(x => x.RevokedAtUtc, DateTime.UtcNow), cancellationToken: cancellationToken);
}

public sealed class AuditLogRepository(MongoStore store) : IAuditLogRepository
{
    public Task WriteAsync(AuditLog entry, CancellationToken cancellationToken) => store.AuditLogs.InsertOneAsync(entry, cancellationToken: cancellationToken);

    public async Task<PagedResult<AuditLog>> SearchAsync(int page, int pageSize, string? userId, string? action, DateTime? fromUtc, DateTime? toUtc, CancellationToken cancellationToken)
    {
        var filter = Builders<AuditLog>.Filter.Empty;
        if (!string.IsNullOrWhiteSpace(userId)) filter &= Builders<AuditLog>.Filter.Eq(x => x.UserId, userId);
        if (!string.IsNullOrWhiteSpace(action)) filter &= Builders<AuditLog>.Filter.Eq(x => x.Action, action);
        if (fromUtc.HasValue) filter &= Builders<AuditLog>.Filter.Gte(x => x.TimestampUtc, fromUtc.Value);
        if (toUtc.HasValue) filter &= Builders<AuditLog>.Filter.Lte(x => x.TimestampUtc, toUtc.Value);
        var total = await store.AuditLogs.CountDocumentsAsync(filter, cancellationToken: cancellationToken);
        var items = await store.AuditLogs.Find(filter).SortByDescending(x => x.TimestampUtc).Skip((page - 1) * pageSize).Limit(pageSize).ToListAsync(cancellationToken);
        return new PagedResult<AuditLog>(items, total, page, pageSize);
    }
}

public sealed class AuditLogService(IAuditLogRepository repository) : IAuditLogService
{
    public Task RecordAsync(AuditLog entry, CancellationToken cancellationToken) => repository.WriteAsync(entry, cancellationToken);
}
