using System.ComponentModel.DataAnnotations;
using System.Security.Claims;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagMiddleware.Application;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Authorize]
[Route("api/conversations")]
public sealed class ConversationsController(IConversationRepository conversations) : ControllerBase
{
    public sealed class CreateRequest { [Required, StringLength(120, MinimumLength = 1)] public required string Title { get; init; } }
    public sealed class ActiveVersionRequest { [Required] public required string VersionId { get; init; } }

    [HttpGet]
    public Task<IReadOnlyCollection<ConversationSummary>> List(CancellationToken cancellationToken) => conversations.ListAsync(UserId, cancellationToken);

    [HttpPost]
    public async Task<IActionResult> Create(CreateRequest request, CancellationToken cancellationToken)
    {
        var conversation = await conversations.CreateAsync(UserId, request.Title.Trim(), cancellationToken);
        return CreatedAtAction(nameof(Get), new { id = conversation.Id }, conversation);
    }

    [HttpGet("{id}")]
    public async Task<IActionResult> Get(string id, CancellationToken cancellationToken)
    {
        var conversation = await conversations.GetAsync(id, UserId, cancellationToken);
        return conversation is null ? NotFound() : Ok(conversation);
    }

    [HttpPut("{conversationId}/messages/{messageId}/active-version")]
    public async Task<IActionResult> SetActiveVersion(string conversationId, string messageId, ActiveVersionRequest request, CancellationToken cancellationToken) =>
        await conversations.SetActiveVersionAsync(conversationId, UserId, messageId, request.VersionId, cancellationToken) ? NoContent() : NotFound();

    private string UserId => User.FindFirstValue(ClaimTypes.NameIdentifier)!;
}
