using MongoDB.Bson;
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

public sealed class ConversationRepository(MongoStore store) : IConversationRepository
{
    public async Task<Conversation> CreateAsync(string userId, string title, CancellationToken cancellationToken)
    {
        var conversation = new Conversation { UserId = userId, Title = title };
        await store.Conversations.InsertOneAsync(conversation, cancellationToken: cancellationToken);
        return conversation;
    }

    public async Task<IReadOnlyCollection<ConversationSummary>> ListAsync(string userId, CancellationToken cancellationToken)
    {
        var conversations = await store.Conversations.Find(x => x.UserId == userId).SortByDescending(x => x.UpdatedAtUtc).ToListAsync(cancellationToken);
        return conversations.Select(x => new ConversationSummary(x.Id, x.Title, x.UpdatedAtUtc, x.Messages.Count)).ToList();
    }

    public Task<Conversation?> GetAsync(string id, string userId, CancellationToken cancellationToken) =>
        store.Conversations.Find(x => x.Id == id && x.UserId == userId).FirstOrDefaultAsync(cancellationToken)!;

    public async Task<PersistedResponse> AddExchangeAsync(string conversationId, string userId, string question, ResponseVersion version, CancellationToken cancellationToken)
    {
        var userMessage = new ConversationMessage { Role = "user", Content = question };
        var assistantMessage = new ConversationMessage { Role = "assistant", Content = version.Content, Versions = [version], ActiveVersionId = version.Id };
        var update = Builders<Conversation>.Update.PushEach(x => x.Messages, [userMessage, assistantMessage]).Set(x => x.UpdatedAtUtc, DateTime.UtcNow);
        var result = await store.Conversations.UpdateOneAsync(x => x.Id == conversationId && x.UserId == userId, update, cancellationToken: cancellationToken);
        if (result.MatchedCount == 0) throw new InvalidOperationException("Conversation was not found.");
        return new PersistedResponse(conversationId, assistantMessage.Id, version.Id);
    }

    public async Task<PersistedResponse?> AddVersionAsync(string conversationId, string userId, string messageId, ResponseVersion version, CancellationToken cancellationToken)
    {
        var filter = Builders<Conversation>.Filter.Where(x => x.Id == conversationId && x.UserId == userId && x.Messages.Any(message => message.Id == messageId && message.Role == "assistant"));
        var update = Builders<Conversation>.Update
            .Push("Messages.$[message].Versions", version)
            .Set("Messages.$[message].ActiveVersionId", version.Id)
            .Set("Messages.$[message].Content", version.Content)
            .Set(x => x.UpdatedAtUtc, DateTime.UtcNow);
        var options = new UpdateOptions { ArrayFilters = [new BsonDocumentArrayFilterDefinition<BsonDocument>(new BsonDocument("message._id", messageId))] };
        var result = await store.Conversations.UpdateOneAsync(filter, update, options, cancellationToken);
        return result.MatchedCount == 0 ? null : new PersistedResponse(conversationId, messageId, version.Id);
    }

    public async Task<bool> SetActiveVersionAsync(string conversationId, string userId, string messageId, string versionId, CancellationToken cancellationToken)
    {
        var filter = Builders<Conversation>.Filter.Where(x => x.Id == conversationId && x.UserId == userId && x.Messages.Any(message => message.Id == messageId && message.Versions.Any(version => version.Id == versionId)));
        var update = Builders<Conversation>.Update.Set("Messages.$[message].ActiveVersionId", versionId);
        var options = new UpdateOptions { ArrayFilters = [new BsonDocumentArrayFilterDefinition<BsonDocument>(new BsonDocument("message._id", messageId))] };
        var result = await store.Conversations.UpdateOneAsync(filter, update, options, cancellationToken);
        return result.ModifiedCount == 1;
    }
}

public sealed class FeedbackRepository(MongoStore store) : IFeedbackRepository
{
    public async Task<ResponseFeedback> UpsertAsync(ResponseFeedback feedback, CancellationToken cancellationToken)
    {
        var filter = Builders<ResponseFeedback>.Filter.Where(x => x.UserId == feedback.UserId && x.VersionId == feedback.VersionId);
        var existing = await store.Feedback.Find(filter).FirstOrDefaultAsync(cancellationToken);
        if (existing is not null) feedback.Id = existing.Id;
        await store.Feedback.ReplaceOneAsync(filter, feedback, new ReplaceOptions { IsUpsert = true }, cancellationToken);
        return feedback;
    }
}
