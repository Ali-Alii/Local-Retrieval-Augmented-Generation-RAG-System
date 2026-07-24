namespace RagMiddleware.Infrastructure;

public sealed class MongoOptions
{
    public const string SectionName = "Mongo";
    public string ConnectionString { get; set; } = "mongodb://127.0.0.1:27017";
    public string DatabaseName { get; set; } = "sentinel";
}

public sealed class RagApiOptions
{
    public const string SectionName = "RagApi";
    public string BaseUrl { get; set; } = "http://127.0.0.1:8000/api/v1/";
    public string? ApiKey { get; set; }
    public int TimeoutSeconds { get; set; } = 330;
}
