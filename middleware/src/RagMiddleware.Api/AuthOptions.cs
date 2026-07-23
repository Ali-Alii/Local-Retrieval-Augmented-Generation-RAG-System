namespace RagMiddleware.Api;

public sealed class JwtOptions
{
    public const string SectionName = "Jwt";
    public string Issuer { get; set; } = "Sentinel.Middleware";
    public string Audience { get; set; } = "Sentinel.React";
    public string SigningKey { get; set; } = string.Empty;
    public int AccessMinutes { get; set; } = 15;
    public int RefreshDays { get; set; } = 14;
}

public sealed class FrontendOptions
{
    public const string SectionName = "Frontend";
    public string AuthCallbackUrl { get; set; } = "http://127.0.0.1:5173";
}
