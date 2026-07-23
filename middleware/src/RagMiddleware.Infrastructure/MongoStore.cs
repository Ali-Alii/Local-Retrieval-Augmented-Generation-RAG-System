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
    }

    public IMongoCollection<User> Users { get; }
    public IMongoCollection<RefreshSession> RefreshSessions { get; }
    public IMongoCollection<AuditLog> AuditLogs { get; }

    public async Task EnsureIndexesAsync(CancellationToken cancellationToken)
    {
        await Users.Indexes.CreateOneAsync(new CreateIndexModel<User>(Builders<User>.IndexKeys.Ascending(x => x.GoogleSubject), new CreateIndexOptions { Unique = true }), cancellationToken: cancellationToken);
        await RefreshSessions.Indexes.CreateOneAsync(new CreateIndexModel<RefreshSession>(Builders<RefreshSession>.IndexKeys.Ascending(x => x.TokenHash), new CreateIndexOptions { Unique = true }), cancellationToken: cancellationToken);
        await RefreshSessions.Indexes.CreateOneAsync(new CreateIndexModel<RefreshSession>(Builders<RefreshSession>.IndexKeys.Ascending(x => x.ExpiresAtUtc), new CreateIndexOptions { ExpireAfter = TimeSpan.Zero }), cancellationToken: cancellationToken);
        await AuditLogs.Indexes.CreateOneAsync(new CreateIndexModel<AuditLog>(Builders<AuditLog>.IndexKeys.Descending(x => x.TimestampUtc)), cancellationToken: cancellationToken);
    }
}
