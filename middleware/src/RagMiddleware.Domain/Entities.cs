namespace RagMiddleware.Domain;

public sealed class User
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public required string GoogleSubject { get; set; }
    public required string Email { get; set; }
    public required string DisplayName { get; set; }
    public string? AvatarUrl { get; set; }
    public List<string> Roles { get; set; } = ["User"];
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    public DateTime LastLoginAtUtc { get; set; } = DateTime.UtcNow;
}

public sealed class RefreshSession
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public required string UserId { get; set; }
    public required string TokenHash { get; set; }
    public DateTime ExpiresAtUtc { get; set; }
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    public DateTime? RevokedAtUtc { get; set; }
}

public sealed class AuditLog
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public string? UserId { get; set; }
    public required string Action { get; set; }
    public required string Endpoint { get; set; }
    public string? RequestSummary { get; set; }
    public int StatusCode { get; set; }
    public string? IpAddress { get; set; }
    public DateTime TimestampUtc { get; set; } = DateTime.UtcNow;
    public long DurationMs { get; set; }
}
