using System.Security.Claims;
using System.Text;
using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi.Models;
using RagMiddleware.Api;
using RagMiddleware.Application;
using RagMiddleware.Infrastructure;

var builder = WebApplication.CreateBuilder(args);

var mongoOptions = builder.Configuration.GetSection(MongoOptions.SectionName).Get<MongoOptions>() ?? new MongoOptions();
var ragOptions = builder.Configuration.GetSection(RagApiOptions.SectionName).Get<RagApiOptions>() ?? new RagApiOptions();
var jwtOptions = builder.Configuration.GetSection(JwtOptions.SectionName).Get<JwtOptions>() ?? new JwtOptions();
var frontendOptions = builder.Configuration.GetSection(FrontendOptions.SectionName).Get<FrontendOptions>() ?? new FrontendOptions();
if (jwtOptions.SigningKey.Length < 32) throw new InvalidOperationException("Jwt:SigningKey must be configured through User Secrets or an environment variable and contain at least 32 characters.");

builder.Services.AddSingleton(mongoOptions);
builder.Services.AddSingleton(ragOptions);
builder.Services.AddSingleton(jwtOptions);
builder.Services.AddSingleton(frontendOptions);
builder.Services.AddSingleton<MongoStore>();
builder.Services.AddHostedService<MongoIndexHostedService>();
builder.Services.AddScoped<IUserRepository, UserRepository>();
builder.Services.AddScoped<IRefreshSessionRepository, RefreshSessionRepository>();
builder.Services.AddScoped<IAuditLogRepository, AuditLogRepository>();
builder.Services.AddScoped<IAuditLogService, AuditLogService>();
builder.Services.AddScoped<ITokenService, TokenService>();
builder.Services.AddHttpClient<IRagApiClient, RagApiClient>(client =>
{
    client.BaseAddress = new Uri(ragOptions.BaseUrl);
    client.Timeout = TimeSpan.FromSeconds(ragOptions.TimeoutSeconds);
});

var authentication = builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuer = true, ValidIssuer = jwtOptions.Issuer,
        ValidateAudience = true, ValidAudience = jwtOptions.Audience,
        ValidateIssuerSigningKey = true, IssuerSigningKey = new SymmetricSecurityKey(Encoding.UTF8.GetBytes(jwtOptions.SigningKey)),
        ValidateLifetime = true, ClockSkew = TimeSpan.FromSeconds(30)
    };
    options.Events = new JwtBearerEvents
    {
        OnMessageReceived = context =>
        {
            if (context.Request.Cookies.TryGetValue("sentinel_access", out var token)) context.Token = token;
            return Task.CompletedTask;
        }
    };
})
.AddCookie("External", options =>
{
    options.Cookie.Name = "sentinel_external";
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Lax;
    options.ExpireTimeSpan = TimeSpan.FromMinutes(10);
});

var googleClientId = builder.Configuration["Authentication:Google:ClientId"];
var googleClientSecret = builder.Configuration["Authentication:Google:ClientSecret"];
if (!string.IsNullOrWhiteSpace(googleClientId) && !string.IsNullOrWhiteSpace(googleClientSecret))
{
    authentication.AddGoogle("Google", options =>
    {
        options.SignInScheme = "External";
        options.ClientId = googleClientId;
        options.ClientSecret = googleClientSecret;
        options.Scope.Add("profile");
        options.SaveTokens = false;
        options.Events.OnCreatingTicket = context =>
        {
            if (context.User.TryGetProperty("picture", out var picture) && context.Identity is not null)
                context.Identity.AddClaim(new Claim("picture", picture.GetString() ?? string.Empty));
            return Task.CompletedTask;
        };
    });
}

builder.Services.AddAuthorization(options => options.AddPolicy("Admin", policy => policy.RequireRole("Admin")));
builder.Services.AddCors(options => options.AddPolicy("frontend", policy => policy.WithOrigins("http://localhost:5173", "http://127.0.0.1:5173").AllowAnyHeader().AllowAnyMethod().AllowCredentials()));
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("auth", context => RateLimitPartition.GetFixedWindowLimiter(context.Connection.RemoteIpAddress?.ToString() ?? "unknown", _ => new FixedWindowRateLimiterOptions { PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
    options.AddPolicy("rag", context => RateLimitPartition.GetFixedWindowLimiter(context.User.FindFirstValue(ClaimTypes.NameIdentifier) ?? context.Connection.RemoteIpAddress?.ToString() ?? "anonymous", _ => new FixedWindowRateLimiterOptions { PermitLimit = 30, Window = TimeSpan.FromMinutes(1), QueueLimit = 0 }));
});
builder.Services.AddProblemDetails();
builder.Services.AddControllers();
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo { Title = "Sentinel RAG Middleware", Version = "v1" });
    options.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme { Type = SecuritySchemeType.Http, Scheme = "bearer", BearerFormat = "JWT", Description = "Middleware JWT. Browser clients use secure HttpOnly cookies." });
});

var app = builder.Build();
app.UseExceptionHandler();
if (app.Environment.IsDevelopment())
{
    app.UseSwagger();
    app.UseSwaggerUI();
}
else app.UseHttpsRedirection();
app.UseCors("frontend");
app.UseMiddleware<AuditMiddleware>();
app.UseAuthentication();
app.UseRateLimiter();
app.UseAuthorization();
app.MapControllers();
app.Run();

public partial class Program;
