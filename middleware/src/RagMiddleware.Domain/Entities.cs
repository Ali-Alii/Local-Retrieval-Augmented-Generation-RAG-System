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

public sealed class Conversation
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public required string UserId { get; set; }
    public required string Title { get; set; }
    public List<ConversationMessage> Messages { get; set; } = [];
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
    public DateTime UpdatedAtUtc { get; set; } = DateTime.UtcNow;
}

public sealed class ConversationMessage
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public required string Role { get; set; }
    public string Content { get; set; } = string.Empty;
    public List<ResponseVersion> Versions { get; set; } = [];
    public string? ActiveVersionId { get; set; }
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
}

public sealed class ResponseVersion
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public required string Content { get; set; }
    public required string Mode { get; set; }
    public required string Runtime { get; set; }
    public long LatencyMs { get; set; }
    public List<CitationSource> Sources { get; set; } = [];
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
}

public sealed class CitationSource
{
    public int Index { get; set; }
    public required string Source { get; set; }
    public int Page { get; set; }
    public required string Text { get; set; }
    public double Score { get; set; }
}

public sealed class ResponseFeedback
{
    public string Id { get; set; } = Guid.NewGuid().ToString("N");
    public required string UserId { get; set; }
    public required string ConversationId { get; set; }
    public required string MessageId { get; set; }
    public required string VersionId { get; set; }
    public required string Rating { get; set; }
    public string? Reason { get; set; }
    public string? Comment { get; set; }
    public DateTime CreatedAtUtc { get; set; } = DateTime.UtcNow;
}
