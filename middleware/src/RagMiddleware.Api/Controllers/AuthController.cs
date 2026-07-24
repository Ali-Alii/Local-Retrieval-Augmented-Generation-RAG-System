using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.AspNetCore.RateLimiting;
using RagMiddleware.Application;

namespace RagMiddleware.Api.Controllers;

[ApiController]
[Route("api/auth")]
public sealed class AuthController(IUserRepository users, ITokenService tokens, IConfiguration configuration, IWebHostEnvironment environment, FrontendOptions frontend) : ControllerBase
{
    [AllowAnonymous]
    [EnableRateLimiting("auth")]
    [HttpGet("login/google")]
    public IActionResult GoogleLogin()
    {
        if (string.IsNullOrWhiteSpace(configuration["Authentication:Google:ClientId"])) return Problem("Google OAuth is not configured. Add credentials through .NET User Secrets.", statusCode: 503);
        return Challenge(new AuthenticationProperties { RedirectUri = Url.Action(nameof(GoogleCallback)) }, ["Google"]);
    }

    [AllowAnonymous]
    [EnableRateLimiting("auth")]
    [HttpGet("google/callback")]
    public async Task<IActionResult> GoogleCallback(CancellationToken cancellationToken)
    {
        var result = await HttpContext.AuthenticateAsync("External");
        if (!result.Succeeded || result.Principal is null) return Unauthorized(new { message = "Google authentication failed." });
        var subject = result.Principal.FindFirstValue(ClaimTypes.NameIdentifier);
        var email = result.Principal.FindFirstValue(ClaimTypes.Email);
        if (string.IsNullOrWhiteSpace(subject) || string.IsNullOrWhiteSpace(email)) return BadRequest(new { message = "Google did not provide the required identity claims." });
        var user = await users.UpsertGoogleUserAsync(new GoogleProfile(subject, email, result.Principal.FindFirstValue(ClaimTypes.Name) ?? email, result.Principal.FindFirstValue("picture")), cancellationToken);
        SetSessionCookies(await tokens.IssueAsync(user, cancellationToken));
        await HttpContext.SignOutAsync("External");
        return Redirect(frontend.AuthCallbackUrl);
    }

    [AllowAnonymous]
    [EnableRateLimiting("auth")]
    [HttpPost("development")]
    public async Task<IActionResult> DevelopmentLogin(CancellationToken cancellationToken)
    {
        if (!environment.IsDevelopment() || !configuration.GetValue<bool>("Authentication:EnableDevelopmentLogin")) return NotFound();
        var user = await users.UpsertGoogleUserAsync(new GoogleProfile("development-user", "developer@localhost", "Local Developer", null), cancellationToken);
        SetSessionCookies(await tokens.IssueAsync(user, cancellationToken));
        return Ok(ToProfile(user));
    }

    [Authorize]
    [HttpGet("me")]
    public async Task<IActionResult> Me(CancellationToken cancellationToken)
    {
        var id = User.FindFirstValue(ClaimTypes.NameIdentifier)!;
        var user = await users.GetByIdAsync(id, cancellationToken);
        return user is null ? Unauthorized() : Ok(ToProfile(user));
    }

    [AllowAnonymous]
    [EnableRateLimiting("auth")]
    [HttpPost("refresh")]
    public async Task<IActionResult> Refresh(CancellationToken cancellationToken)
    {
        if (!Request.Cookies.TryGetValue("sentinel_refresh", out var refreshToken)) return Unauthorized();
        var session = await tokens.RefreshAsync(refreshToken, cancellationToken);
        if (session is null) return Unauthorized();
        SetSessionCookies(session);
        return Ok(new { ok = true });
    }

    [AllowAnonymous]
    [HttpPost("logout")]
    public async Task<IActionResult> Logout(CancellationToken cancellationToken)
    {
        if (Request.Cookies.TryGetValue("sentinel_refresh", out var refreshToken)) await tokens.RevokeAsync(refreshToken, cancellationToken);
        Response.Cookies.Delete("sentinel_access");
        Response.Cookies.Delete("sentinel_refresh", new CookieOptions { Path = "/api/auth" });
        return Ok(new { ok = true });
    }

    private void SetSessionCookies(SessionTokens session)
    {
        var secure = !environment.IsDevelopment();
        Response.Cookies.Append("sentinel_access", session.AccessToken, new CookieOptions { HttpOnly = true, Secure = secure, SameSite = SameSiteMode.Lax, Expires = session.AccessExpiresAtUtc });
        Response.Cookies.Append("sentinel_refresh", session.RefreshToken, new CookieOptions { HttpOnly = true, Secure = secure, SameSite = SameSiteMode.Lax, Expires = session.RefreshExpiresAtUtc, Path = "/api/auth" });
    }

    private static UserProfile ToProfile(RagMiddleware.Domain.User user) => new(user.Id, user.Email, user.DisplayName, user.AvatarUrl, user.Roles);
}
