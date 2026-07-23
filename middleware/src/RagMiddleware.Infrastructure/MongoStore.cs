using MongoDB.Driver;
using RagMiddleware.Domain;

namespace RagMiddleware.Infrastructure;

public sealed class MongoStore
{
    public MongoStore(MongoOptions options)
    {
        var database = new MongoClient(options.ConnectionString).GetDatabase(options.DatabaseName);
        Users = database.GetCollection<User>("users");
        RefreshSessions = database.GetCollection<RefreshSession>("refresh_sessions");
        AuditLogs = database.GetCollection<AuditLog>("audit_logs");
        Conversations = database.GetCollection<Conversation>("conversations");
        Feedback = database.GetCollection<ResponseFeedback>("response_feedback");
    }

    public IMongoCollection<User> Users { get; }
    public IMongoCollection<RefreshSession> RefreshSessions { get; }
    public IMongoCollection<AuditLog> AuditLogs { get; }
    public IMongoCollection<Conversation> Conversations { get; }
    public IMongoCollection<ResponseFeedback> Feedback { get; }

    public async Task EnsureIndexesAsync(CancellationToken cancellationToken)
    {
        await Users.Indexes.CreateOneAsync(new CreateIndexModel<User>(Builders<User>.IndexKeys.Ascending(x => x.GoogleSubject), new CreateIndexOptions { Unique = true }), cancellationToken: cancellationToken);
        await RefreshSessions.Indexes.CreateOneAsync(new CreateIndexModel<RefreshSession>(Builders<RefreshSession>.IndexKeys.Ascending(x => x.TokenHash), new CreateIndexOptions { Unique = true }), cancellationToken: cancellationToken);
        await RefreshSessions.Indexes.CreateOneAsync(new CreateIndexModel<RefreshSession>(Builders<RefreshSession>.IndexKeys.Ascending(x => x.ExpiresAtUtc), new CreateIndexOptions { ExpireAfter = TimeSpan.Zero }), cancellationToken: cancellationToken);
        await AuditLogs.Indexes.CreateOneAsync(new CreateIndexModel<AuditLog>(Builders<AuditLog>.IndexKeys.Descending(x => x.TimestampUtc)), cancellationToken: cancellationToken);
        await Conversations.Indexes.CreateOneAsync(new CreateIndexModel<Conversation>(Builders<Conversation>.IndexKeys.Ascending(x => x.UserId).Descending(x => x.UpdatedAtUtc)), cancellationToken: cancellationToken);
        await Feedback.Indexes.CreateOneAsync(new CreateIndexModel<ResponseFeedback>(Builders<ResponseFeedback>.IndexKeys.Ascending(x => x.UserId).Ascending(x => x.VersionId), new CreateIndexOptions { Unique = true }), cancellationToken: cancellationToken);
    }
}
