using RagMiddleware.Api;
using RagMiddleware.Application;
using RagMiddleware.Domain;

namespace RagMiddleware.Tests;

public sealed class TokenServiceTests
{
    [Fact]
    public async Task IssueAndRefreshRotatesRefreshToken()
    {
        var user = TestUser();
        var sessions = new MemorySessions();
        var service = new TokenService(new JwtOptions { SigningKey = new string('x', 64) }, sessions, new MemoryUsers(user));

        var first = await service.IssueAsync(user, CancellationToken.None);
        var second = await service.RefreshAsync(first.RefreshToken, CancellationToken.None);

        Assert.NotNull(second);
        Assert.NotEqual(first.RefreshToken, second!.RefreshToken);
        Assert.DoesNotContain(sessions.StoredHashes, hash => hash == first.RefreshToken);
    }

    [Fact]
    public async Task RevokedRefreshTokenCannotBeReused()
    {
        var user = TestUser();
        var sessions = new MemorySessions();
        var service = new TokenService(new JwtOptions { SigningKey = new string('y', 64) }, sessions, new MemoryUsers(user));
        var issued = await service.IssueAsync(user, CancellationToken.None);

        await service.RevokeAsync(issued.RefreshToken, CancellationToken.None);

        Assert.Null(await service.RefreshAsync(issued.RefreshToken, CancellationToken.None));
    }

    private static User TestUser() => new() { GoogleSubject = "google-1", Email = "user@example.com", DisplayName = "Test User" };

    private sealed class MemoryUsers(User user) : IUserRepository
    {
        public Task<User?> GetByIdAsync(string id, CancellationToken cancellationToken) => Task.FromResult<User?>(id == user.Id ? user : null);
        public Task<User> UpsertGoogleUserAsync(GoogleProfile profile, CancellationToken cancellationToken) => Task.FromResult(user);
    }

    private sealed class MemorySessions : IRefreshSessionRepository
    {
        private readonly Dictionary<string, RefreshSession> _sessions = [];
        public IEnumerable<string> StoredHashes => _sessions.Keys;
        public Task CreateAsync(RefreshSession session, CancellationToken cancellationToken) { _sessions[session.TokenHash] = session; return Task.CompletedTask; }
        public Task<RefreshSession?> GetActiveByHashAsync(string tokenHash, CancellationToken cancellationToken) => Task.FromResult(_sessions.TryGetValue(tokenHash, out var session) && session.RevokedAtUtc is null ? session : null);
        public Task RevokeAsync(string tokenHash, CancellationToken cancellationToken) { if (_sessions.TryGetValue(tokenHash, out var session)) session.RevokedAtUtc = DateTime.UtcNow; return Task.CompletedTask; }
        public Task RevokeAllForUserAsync(string userId, CancellationToken cancellationToken) { foreach (var session in _sessions.Values.Where(x => x.UserId == userId)) session.RevokedAtUtc = DateTime.UtcNow; return Task.CompletedTask; }
    }
}
