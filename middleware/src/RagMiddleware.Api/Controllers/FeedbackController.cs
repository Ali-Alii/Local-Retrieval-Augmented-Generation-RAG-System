using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagMiddleware.Application;
using RagMiddleware.Domain;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/feedback")]
public sealed class FeedbackController(IFeedbackRepository feedback, IConversationRepository conversations) : ControllerBase
{
    public sealed class FeedbackRequest
    {
        [Required] public required string ConversationId { get; init; }
        [Required] public required string MessageId { get; init; }
        [Required] public required string VersionId { get; init; }
        [Required, RegularExpression("^(up|down)$")] public required string Rating { get; init; }
        [StringLength(80)] public string? Reason { get; init; }
        [StringLength(1000)] public string? Comment { get; init; }
    }

    [HttpPost]
    public async Task<IActionResult> Submit(FeedbackRequest request, CancellationToken cancellationToken)
    {
        var userId = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var conversation = await conversations.GetAsync(request.ConversationId, userId, cancellationToken);
        var validVersion = conversation?.Messages.Any(message => message.Id == request.MessageId && message.Versions.Any(version => version.Id == request.VersionId)) == true;
        if (!validVersion) return NotFound(new { message = "The response version was not found." });
        if (request.Rating == "down" && string.IsNullOrWhiteSpace(request.Reason)) return BadRequest(new { message = "A reason is required for negative feedback." });
        var saved = await feedback.UpsertAsync(new ResponseFeedback
        {
            UserId = userId, ConversationId = request.ConversationId, MessageId = request.MessageId,
            VersionId = request.VersionId, Rating = request.Rating, Reason = request.Reason, Comment = request.Comment
        }, cancellationToken);
        return Ok(new { saved.Id, saved.Rating, saved.CreatedAtUtc });
    }
}
