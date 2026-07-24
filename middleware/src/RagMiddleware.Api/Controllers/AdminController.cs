using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using RagMiddleware.Application;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Authorize(Roles = "Admin")]
[Route("api/admin")]
public sealed class AdminController(IAuditLogRepository auditLogs) : ControllerBase
{
    [HttpGet("audit-logs")]
    public async Task<IActionResult> AuditLogs([FromQuery] int page = 1, [FromQuery] int pageSize = 50, [FromQuery] string? userId = null, [FromQuery] string? action = null, [FromQuery] DateTime? fromUtc = null, [FromQuery] DateTime? toUtc = null, CancellationToken cancellationToken = default)
    {
        page = Math.Max(1, page);
        pageSize = Math.Clamp(pageSize, 1, 100);
        return Ok(await auditLogs.SearchAsync(page, pageSize, userId, action, fromUtc, toUtc, cancellationToken));
    }
}
