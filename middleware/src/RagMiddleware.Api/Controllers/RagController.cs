using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using System.Text;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using RagMiddleware.Application;
using RagMiddleware.Domain;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Authorize]
[EnableRateLimiting("rag")]
[Route("api/rag")]
public sealed class RagController(IRagApiClient rag, IConversationRepository conversations, ILogger<RagController> logger) : ControllerBase
{
    public sealed class QueryRequest
    {
        [Required, StringLength(1000, MinimumLength = 1)]
        public required string Question { get; init; }
        public string? ConversationId { get; init; }
        public string? AssistantMessageId { get; init; }
    }

    [HttpGet("status")]
    public async Task<IActionResult> Status(CancellationToken cancellationToken) => Content((await rag.GetStatusAsync(cancellationToken)).RootElement.GetRawText(), "application/json");

    [HttpPost("query")]
    public async Task<IActionResult> Query(QueryRequest request, CancellationToken cancellationToken) => Content((await rag.QueryAsync(request.Question.Trim(), cancellationToken)).RootElement.GetRawText(), "application/json");

    [HttpPost("query/stream")]
    public async Task Stream(QueryRequest request, CancellationToken cancellationToken)
    {
        if (string.IsNullOrWhiteSpace(request.ConversationId))
        {
            Response.StatusCode = StatusCodes.Status400BadRequest;
            await Response.WriteAsJsonAsync(new { message = "A conversation ID is required." }, cancellationToken);
            return;
        }
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        if (await conversations.GetAsync(request.ConversationId, userId, cancellationToken) is null)
        {
            Response.StatusCode = StatusCodes.Status404NotFound;
            await Response.WriteAsJsonAsync(new { message = "Conversation not found." }, cancellationToken);
            return;
        }

        try
        {
            using var upstream = await rag.StreamQueryAsync(request.Question.Trim(), cancellationToken);
            Response.StatusCode = (int)upstream.StatusCode;
            Response.ContentType = "text/event-stream";
            Response.Headers.CacheControl = "no-cache";
            Response.Headers.Append("X-Accel-Buffering", "no");

            var answer = new StringBuilder();
            var sources = new List<CitationSource>();
            JsonElement? done = null;
            await using var stream = await upstream.Content.ReadAsStreamAsync(cancellationToken);
            using var reader = new StreamReader(stream);
            string? eventName = null;
            string? eventData = null;
            while (await reader.ReadLineAsync(cancellationToken) is { } line)
            {
                if (line.StartsWith("event: ")) eventName = line[7..];
                else if (line.StartsWith("data: ")) eventData = line[6..];
                else if (line.Length == 0 && eventName is not null && eventData is not null)
                {
                    using var document = JsonDocument.Parse(eventData);
                    var payload = document.RootElement.Clone();
                    if (eventName == "token" && payload.TryGetProperty("content", out var content)) answer.Append(content.GetString());
                    if (eventName == "sources" && payload.TryGetProperty("items", out var items))
                    {
                        var index = 1;
                        foreach (var item in items.EnumerateArray())
                        {
                            sources.Add(new CitationSource
                            {
                                Index = index++, Source = item.GetProperty("source").GetString() ?? "document",
                                Page = item.GetProperty("page").GetInt32(), Text = item.GetProperty("text").GetString() ?? string.Empty,
                                Score = item.TryGetProperty("score", out var score) ? score.GetDouble() : 0
                            });
                        }
                    }
                    if (eventName == "done") done = payload;
                    else await WriteEventAsync(eventName, payload.GetRawText(), cancellationToken);
                    eventName = eventData = null;
                }
            }

            var donePayload = done ?? JsonDocument.Parse("{\"mode\":\"unknown\",\"runtime\":\"unknown\",\"latency_ms\":0}").RootElement.Clone();
            var version = new ResponseVersion
            {
                Content = answer.ToString(), Mode = donePayload.GetProperty("mode").GetString() ?? "unknown",
                Runtime = donePayload.GetProperty("runtime").GetString() ?? "unknown",
                LatencyMs = donePayload.TryGetProperty("latency_ms", out var latency) ? latency.GetInt64() : 0,
                Sources = sources
            };
            PersistedResponse? persisted = string.IsNullOrWhiteSpace(request.AssistantMessageId)
                ? await conversations.AddExchangeAsync(request.ConversationId, userId, request.Question.Trim(), version, cancellationToken)
                : await conversations.AddVersionAsync(request.ConversationId, userId, request.AssistantMessageId, version, cancellationToken);
            if (persisted is null)
            {
                await WriteEventAsync("error", JsonSerializer.Serialize(new { message = "The response message could not be found." }), cancellationToken);
                return;
            }
            await WriteEventAsync("persisted", JsonSerializer.Serialize(new { conversationId = persisted.ConversationId, messageId = persisted.MessageId, versionId = persisted.VersionId }), cancellationToken);
            await WriteEventAsync("done", donePayload.GetRawText(), cancellationToken);
        }
        catch (Exception error)
        {
            logger.LogError(error, "SSE proxy failed while calling the Python RAG service");
            if (!Response.HasStarted) throw;
            await WriteEventAsync("error", JsonSerializer.Serialize(new { message = "The streamed response could not be completed." }), cancellationToken);
        }
    }

    [HttpGet("evaluation")]
    public async Task<IActionResult> Evaluation(CancellationToken cancellationToken) => Content((await rag.GetEvaluationAsync(cancellationToken)).RootElement.GetRawText(), "application/json");

    private async Task WriteEventAsync(string eventName, string json, CancellationToken cancellationToken)
    {
        await Response.WriteAsync($"event: {eventName}\ndata: {json}\n\n", cancellationToken);
        await Response.Body.FlushAsync(cancellationToken);
    }
}
