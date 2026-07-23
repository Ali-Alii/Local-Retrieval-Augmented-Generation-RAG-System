using RagMiddleware.Infrastructure;

namespace RagMiddleware.Api;

public sealed class MongoIndexHostedService(MongoStore store) : IHostedService
{
    public Task StartAsync(CancellationToken cancellationToken) => store.EnsureIndexesAsync(cancellationToken);
    public Task StopAsync(CancellationToken cancellationToken) => Task.CompletedTask;
}
