using System.IdentityModel.Tokens.Jwt;
using System.Security.Claims;
using System.Security.Cryptography;
using System.Text;
using Microsoft.IdentityModel.Tokens;
using RagMiddleware.Application;
using RagMiddleware.Domain;

namespace RagMiddleware.Api;

public sealed class TokenService(JwtOptions options, IRefreshSessionRepository sessions, IUserRepository users) : ITokenService
{
    public async Task<SessionTokens> IssueAsync(User user, CancellationToken cancellationToken)
    {
        var accessExpiry = DateTime.UtcNow.AddMinutes(options.AccessMinutes);
        var refreshExpiry = DateTime.UtcNow.AddDays(options.RefreshDays);
        var refreshToken = Convert.ToBase64String(RandomNumberGenerator.GetBytes(48));
        await sessions.CreateAsync(new RefreshSession { UserId = user.Id, TokenHash = Hash(refreshToken), ExpiresAtUtc = refreshExpiry }, cancellationToken);
        return new SessionTokens(CreateAccessToken(user, accessExpiry), accessExpiry, refreshToken, refreshExpiry);
    }

    public async Task<SessionTokens?> RefreshAsync(string refreshToken, CancellationToken cancellationToken)
    {
        var hash = Hash(refreshToken);
        var session = await sessions.GetActiveByHashAsync(hash, cancellationToken);
        if (session is null) return null;
        var user = await users.GetByIdAsync(session.UserId, cancellationToken);
        if (user is null) return null;
        await sessions.RevokeAsync(hash, cancellationToken);
        return await IssueAsync(user, cancellationToken);
    }

    public Task RevokeAsync(string refreshToken, CancellationToken cancellationToken) => sessions.RevokeAsync(Hash(refreshToken), cancellationToken);

    private string CreateAccessToken(User user, DateTime expiry)
    {
        var claims = new List<Claim>
        {
            new(ClaimTypes.NameIdentifier, user.Id), new(ClaimTypes.Email, user.Email), new(ClaimTypes.Name, user.DisplayName)
        };
        claims.AddRange(user.Roles.Select(role => new Claim(ClaimTypes.Role, role)));
        var credentials = new SigningCredentials(new SymmetricSecurityKey(Encoding.UTF8.GetBytes(options.SigningKey)), SecurityAlgorithms.HmacSha256);
        return new JwtSecurityTokenHandler().WriteToken(new JwtSecurityToken(options.Issuer, options.Audience, claims, expires: expiry, signingCredentials: credentials));
    }

    internal static string Hash(string token) => Convert.ToHexString(SHA256.HashData(Encoding.UTF8.GetBytes(token)));
}
