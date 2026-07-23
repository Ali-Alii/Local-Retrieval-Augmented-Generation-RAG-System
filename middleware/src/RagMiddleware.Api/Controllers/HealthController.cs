using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Route("health")]
public sealed class HealthController : ControllerBase
{
    [AllowAnonymous]
    [HttpGet]
    public IActionResult Get() => Ok(new { status = "ok", service = "rag-middleware", storage = "mongodb" });
}
