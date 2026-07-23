using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using RagMiddleware.Application;

namespace RagMiddleware.Infrastructure;

public sealed class RagApiClient(HttpClient client, RagApiOptions options) : IRagApiClient
{
    public Task<JsonDocument> GetStatusAsync(CancellationToken cancellationToken) => GetJsonAsync("status", cancellationToken);
    public Task<JsonDocument> GetEvaluationAsync(CancellationToken cancellationToken) => GetJsonAsync("evaluation", cancellationToken);

    public async Task<JsonDocument> QueryAsync(string question, CancellationToken cancellationToken)
    {
        using var response = await SendWithRetryAsync(() => new HttpRequestMessage(HttpMethod.Post, "ask") { Content = JsonContent.Create(new { question }) }, HttpCompletionOption.ResponseContentRead, cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
        return (await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken));
    }

    public async Task<HttpResponseMessage> StreamQueryAsync(string question, CancellationToken cancellationToken)
    {
        var response = await SendWithRetryAsync(() => new HttpRequestMessage(HttpMethod.Post, "ask/stream") { Content = JsonContent.Create(new { question }) }, HttpCompletionOption.ResponseHeadersRead, cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
        return response;
    }

    public async Task SendFeedbackAsync(JsonElement payload, CancellationToken cancellationToken)
    {
        using var response = await SendWithRetryAsync(() => new HttpRequestMessage(HttpMethod.Post, "feedback") { Content = JsonContent.Create(payload) }, HttpCompletionOption.ResponseContentRead, cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
    }

    private async Task<JsonDocument> GetJsonAsync(string path, CancellationToken cancellationToken)
    {
        using var response = await SendWithRetryAsync(() => new HttpRequestMessage(HttpMethod.Get, path), HttpCompletionOption.ResponseContentRead, cancellationToken);
        await EnsureSuccessAsync(response, cancellationToken);
        return await JsonDocument.ParseAsync(await response.Content.ReadAsStreamAsync(cancellationToken), cancellationToken: cancellationToken);
    }

    private async Task<HttpResponseMessage> SendWithRetryAsync(Func<HttpRequestMessage> requestFactory, HttpCompletionOption completion, CancellationToken cancellationToken)
    {
        Exception? lastError = null;
        for (var attempt = 1; attempt <= 3; attempt++)
        {
            try
            {
                using var request = requestFactory();
                if (!string.IsNullOrWhiteSpace(options.ApiKey)) request.Headers.TryAddWithoutValidation("X-API-Key", options.ApiKey);
                var response = await client.SendAsync(request, completion, cancellationToken);
                if (response.StatusCode is not HttpStatusCode.RequestTimeout && (int)response.StatusCode < 500) return response;
                if (attempt == 3) return response;
                response.Dispose();
            }
            catch (HttpRequestException error) when (attempt < 3)
            {
                lastError = error;
            }
            await Task.Delay(TimeSpan.FromMilliseconds(200 * Math.Pow(2, attempt - 1)), cancellationToken);
        }
        throw new HttpRequestException("The Python RAG service is unavailable.", lastError);
    }

    private static async Task EnsureSuccessAsync(HttpResponseMessage response, CancellationToken cancellationToken)
    {
        if (response.IsSuccessStatusCode) return;
        _ = await response.Content.ReadAsStringAsync(cancellationToken);
        throw new HttpRequestException("The Python RAG service returned an error.", null, response.StatusCode);
    }
}
