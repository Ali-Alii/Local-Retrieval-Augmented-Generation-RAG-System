using System.ComponentModel.DataAnnotations;
using System.Text.Json;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using RagMiddleware.Application;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Authorize]
[EnableRateLimiting("rag")]
[Route("api/rag")]
public sealed class RagController(IRagApiClient rag, ILogger<RagController> logger) : ControllerBase
{
    public sealed class QueryRequest
    {
        [Required, StringLength(1000, MinimumLength = 1)]
        public required string Question { get; init; }
    }

    [HttpGet("status")]
    public async Task<IActionResult> Status(CancellationToken cancellationToken) => Content((await rag.GetStatusAsync(cancellationToken)).RootElement.GetRawText(), "application/json");

    [HttpPost("query")]
    public async Task<IActionResult> Query(QueryRequest request, CancellationToken cancellationToken) => Content((await rag.QueryAsync(request.Question.Trim(), cancellationToken)).RootElement.GetRawText(), "application/json");

    [HttpPost("query/stream")]
    public async Task Stream(QueryRequest request, CancellationToken cancellationToken)
    {
        try
        {
            using var upstream = await rag.StreamQueryAsync(request.Question.Trim(), cancellationToken);
            Response.StatusCode = (int)upstream.StatusCode;
            Response.ContentType = "text/event-stream";
            Response.Headers.CacheControl = "no-cache";
            Response.Headers.Append("X-Accel-Buffering", "no");
            await using var stream = await upstream.Content.ReadAsStreamAsync(cancellationToken);
            await stream.CopyToAsync(Response.Body, cancellationToken);
        }
        catch (Exception error)
        {
            logger.LogError(error, "SSE proxy failed while calling the Python RAG service");
            throw;
        }
    }

    [HttpGet("evaluation")]
    public async Task<IActionResult> Evaluation(CancellationToken cancellationToken) => Content((await rag.GetEvaluationAsync(cancellationToken)).RootElement.GetRawText(), "application/json");

    [HttpPost("feedback")]
    public async Task<IActionResult> Feedback([FromBody] JsonElement payload, CancellationToken cancellationToken)
    {
        await rag.SendFeedbackAsync(payload, cancellationToken);
        return Ok(new { ok = true });
    }
}
